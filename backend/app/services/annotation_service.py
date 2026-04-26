import json
import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from fastapi import HTTPException

from app.core.normalization import collect_aliases, normalize_text
from app.core.config import get_settings
from app.models.concept import Concept, ConceptPage, UserConceptState
from app.models.document import Document, DocumentEntity
from app.schemas.llm import EntityCandidate, LearningKeyword
from app.services.document_service import get_document_or_404
from app.services.llm_service import llm_service


@dataclass
class EntityMatch:
    concept: Concept
    entity: EntityCandidate
    document_id: int
    raw_text: str
    start: int
    end: int


def resolve_or_create_concept(db: Session, candidate: EntityCandidate, document: Document) -> Concept:
    aliases = collect_aliases(candidate.text) | collect_aliases(candidate.normalized)
    for alias in candidate.aliases:
        aliases |= collect_aliases(alias)
    display_aliases = sorted(
        {
            candidate.normalized,
            *candidate.aliases,
            *aliases,
        }
        - {candidate.text, ""}
    )
    normalized = normalize_text(candidate.normalized or candidate.text)
    statement = select(Concept).where(Concept.concept_type == candidate.type)
    concepts = db.execute(statement).scalars().all()
    for concept in concepts:
        concept_normalized = concept.normalized_name or normalize_text(concept.canonical_name)
        if concept_normalized in aliases or concept_normalized == normalized:
            if not concept.normalized_name:
                concept.normalized_name = concept_normalized
                db.add(concept)
            merged_aliases = sorted({*concept.aliases, *display_aliases} - {concept.canonical_name, ""})
            concept.aliases_json = json.dumps(merged_aliases, ensure_ascii=False)
            db.add(concept)
            return concept

    concept = Concept(
        canonical_name=candidate.text.strip(),
        normalized_name=normalized,
        concept_type=candidate.type,
        generation_status="stub",
        short_explanation=candidate.reason,
        aliases_json=json.dumps(display_aliases, ensure_ascii=False),
    )
    db.add(concept)
    db.flush()

    state = UserConceptState(concept_id=concept.id, status="unknown")
    db.add(state)
    db.flush()
    return concept


def _protected_ranges(markdown_content: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    patterns = [
        r"```[\s\S]*?```",
        r"`[^`\n]+`",
        r"\$\$[\s\S]*?\$\$",
        r"\\\[[\s\S]*?\\\]",
        r"(?<!\$)\$[^$\n]+\$(?!\$)",
        r"!?\[[^\]]+\]\([^)]+\)",
    ]
    for pattern in patterns:
        ranges.extend((match.start(), match.end()) for match in re.finditer(pattern, markdown_content))

    cursor = 0
    for line in markdown_content.splitlines(keepends=True):
        line_start = cursor
        line_end = cursor + len(line)
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            ranges.append((line_start, line_end))
        cursor = line_end
    return sorted(ranges)


def _overlaps_ranges(start: int, end: int, ranges: list[tuple[int, int]]) -> bool:
    return any(start < protected_end and end > protected_start for protected_start, protected_end in ranges)


def locate_first_occurrence(
    markdown_content: str,
    candidate: EntityCandidate,
    protected: list[tuple[int, int]] | None = None,
) -> tuple[int, int, str] | None:
    protected = protected or []
    aliases = collect_aliases(candidate.text) | collect_aliases(candidate.normalized)
    for alias in candidate.aliases:
        aliases |= collect_aliases(alias)
    aliases = sorted(aliases, key=len, reverse=True)
    for alias in aliases:
        pattern = re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE)
        for match in pattern.finditer(markdown_content):
            if not _overlaps_ranges(match.start(), match.end(), protected):
                return match.start(), match.end(), match.group(0)

    raw = candidate.text.strip()
    if raw:
        pattern = re.compile(re.escape(raw), re.IGNORECASE)
        for match in pattern.finditer(markdown_content):
            if not _overlaps_ranges(match.start(), match.end(), protected):
                return match.start(), match.end(), match.group(0)
    return None


def annotate_first_occurrences(markdown_content: str, matches: list[EntityMatch]) -> str:
    ordered = sorted(matches, key=lambda item: item.start)
    output: list[str] = []
    cursor = 0
    for match in ordered:
        if match.start < cursor:
            continue
        output.append(markdown_content[cursor:match.start])
        output.append(f"[{match.raw_text}](/concepts/{match.concept.id}?documentId={match.document_id})")
        cursor = match.end
    output.append(markdown_content[cursor:])
    return "".join(output)


def annotate_document(db: Session, document_id: int) -> Document:
    settings = get_settings()
    document = get_document_or_404(db=db, document_id=document_id)
    if not document.markdown_content:
        raise HTTPException(status_code=400, detail="Document must be parsed before annotation.")

    if document.learning_keywords:
        candidates = []
        for item in document.learning_keywords:
            try:
                keyword = LearningKeyword.model_validate(item)
            except Exception:
                continue
            candidates.append(
                EntityCandidate(
                    text=keyword.text,
                    type=keyword.type if keyword.type in {"term", "parameter", "formula"} else "term",
                    normalized=keyword.normalized or normalize_text(keyword.text),
                    reason=keyword.reason,
                    aliases=keyword.aliases,
                )
            )
    else:
        candidates = llm_service.extract_entities(document.markdown_content)
    candidates = candidates[: settings.max_annotation_entities]
    db.execute(delete(DocumentEntity).where(DocumentEntity.document_id == document.id))
    db.commit()

    matches: list[EntityMatch] = []
    occupied: list[tuple[int, int]] = []
    protected = _protected_ranges(document.markdown_content)

    for candidate in candidates:
        occurrence = locate_first_occurrence(document.markdown_content, candidate, protected=protected)
        if not occurrence:
            continue
        start, end, raw_text = occurrence
        if any(not (end <= existing_start or start >= existing_end) for existing_start, existing_end in occupied):
            continue

        concept = resolve_or_create_concept(db=db, candidate=candidate, document=document)
        entity = DocumentEntity(
            document_id=document.id,
            concept_id=concept.id,
            raw_text=raw_text,
            normalized_text=normalize_text(candidate.normalized),
            entity_type=candidate.type,
            first_occurrence_only=True,
            position_start=start,
            position_end=end,
        )
        db.add(entity)
        db.flush()
        matches.append(
            EntityMatch(
                concept=concept,
                entity=candidate,
                document_id=document.id,
                raw_text=raw_text,
                start=start,
                end=end,
            )
        )
        occupied.append((start, end))

    document.annotated_markdown = annotate_first_occurrences(document.markdown_content, matches)
    document.status = "annotated"
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
