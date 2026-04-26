import hashlib
import json
import re
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.normalization import collect_aliases, normalize_text
from app.models.document import Document
from app.models.keyword import KeywordNode
from app.schemas.keyword import KeywordDetail, KeywordExplanationContent, KeywordLink, KeywordPathItem
from app.schemas.llm import EntityCandidate, LearningKeyword
from app.services.heuristics import extract_entities_fallback
from app.services.llm_service import LLMGenerationError, llm_service


GENERIC_KEYWORDS = {
    "method",
    "model",
    "data",
    "dataset",
    "paper",
    "result",
    "experiment",
    "task",
    "approach",
    "problem",
    "input",
    "output",
    "training",
    "testing",
    "section",
    "figure",
    "table",
    "performance",
    "baseline",
    "proposed method",
}


@dataclass
class KeywordMatch:
    node: KeywordNode
    raw_text: str
    start: int
    end: int


def _protected_ranges(markdown_content: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    patterns = [
        r"```[\s\S]*?```",
        r"`[^`\n]+`",
        r"\$\$[\s\S]*?\$\$",
        r"\\\[[\s\S]+?\\\]",
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


def _term_needs_boundary(term: str) -> bool:
    return bool(re.match(r"^[A-Za-z0-9_]", term) or re.search(r"[A-Za-z0-9_]$", term))


def _find_term(text: str, term: str, start: int = 0) -> re.Match[str] | None:
    flags = re.IGNORECASE
    if _term_needs_boundary(term):
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(term)}(?![A-Za-z0-9_])", flags)
    else:
        pattern = re.compile(re.escape(term), flags)
    return pattern.search(text, start)


def _candidate_aliases(candidate: EntityCandidate) -> list[str]:
    aliases = collect_aliases(candidate.text) | collect_aliases(candidate.normalized)
    aliases |= {candidate.text.strip(), candidate.normalized.strip()}
    for alias in candidate.aliases:
        aliases |= collect_aliases(alias)
        aliases.add(alias.strip())
    return sorted({alias for alias in aliases if alias}, key=len, reverse=True)


def locate_first_occurrence(
    markdown_content: str,
    candidate: EntityCandidate,
    protected: list[tuple[int, int]] | None = None,
) -> tuple[int, int, str] | None:
    protected = protected or []
    for alias in _candidate_aliases(candidate):
        cursor = 0
        while True:
            match = _find_term(markdown_content, alias, cursor)
            if not match:
                break
            if not _overlaps_ranges(match.start(), match.end(), protected):
                return match.start(), match.end(), match.group(0)
            cursor = match.end()
    return None


def _source_sentence(text: str, start: int, end: int, limit: int = 500) -> str:
    left_candidates = [text.rfind(marker, 0, start) for marker in ["。", "！", "？", ".", "!", "?", "\n"]]
    right_candidates = [text.find(marker, end) for marker in ["。", "！", "？", ".", "!", "?", "\n"]]
    left = max(left_candidates)
    right_values = [value for value in right_candidates if value >= 0]
    right = min(right_values) if right_values else min(len(text), end + limit)
    sentence = text[left + 1 : right + 1].strip()
    return " ".join(sentence.split())[:limit]


def _source_context(text: str, start: int, end: int, limit: int = 1800) -> str:
    radius = max(300, limit // 2)
    context = text[max(0, start - radius) : min(len(text), end + radius)]
    return " ".join(context.split())[:limit]


def _valid_candidate(candidate: EntityCandidate, current_keyword: str | None = None) -> bool:
    text = candidate.text.strip()
    if not text or "\n" in text:
        return False
    normalized = normalize_text(candidate.normalized or text)
    if normalized in GENERIC_KEYWORDS or text.lower() in GENERIC_KEYWORDS:
        return False
    if current_keyword and normalized == normalize_text(current_keyword):
        return False
    if len(text) > 80:
        return False
    if len(text) < 2 and candidate.type not in {"formula", "parameter"}:
        return False
    if len(text) == 1 and candidate.type in {"formula", "parameter"} and not re.match(r"[A-Za-z_\\]", text):
        return False
    if re.fullmatch(r"[\W_]+", text, flags=re.UNICODE):
        return False
    return True


def _stable_key(paper_id: int, normalized_keyword: str, parent_keyword_id: int | None) -> str:
    parent = str(parent_keyword_id) if parent_keyword_id is not None else "root"
    raw = f"{paper_id}:{parent}:{normalized_keyword}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _resolve_or_create_keyword_node(
    db: Session,
    document: Document,
    candidate: EntityCandidate,
    raw_text: str,
    source_sentence: str,
    source_context: str,
    parent_keyword_id: int | None,
    level: int,
) -> KeywordNode:
    normalized = normalize_text(candidate.normalized or candidate.text)
    key = _stable_key(document.id, normalized, parent_keyword_id)
    existing = db.execute(select(KeywordNode).where(KeywordNode.stable_key == key)).scalar_one_or_none()
    aliases = sorted({candidate.normalized, *candidate.aliases, *_candidate_aliases(candidate)} - {candidate.text, raw_text, ""})
    if existing:
        if source_context and not existing.source_context:
            existing.source_context = source_context
        if source_sentence and not existing.source_sentence:
            existing.source_sentence = source_sentence
        merged_aliases = sorted({*existing.aliases, *aliases} - {existing.keyword, ""})
        existing.aliases_json = json.dumps(merged_aliases, ensure_ascii=False)
        db.add(existing)
        db.flush()
        return existing

    node = KeywordNode(
        paper_id=document.id,
        keyword=raw_text.strip() or candidate.text.strip(),
        normalized_keyword=normalized,
        keyword_type=candidate.type if candidate.type else "term",
        source_sentence=source_sentence,
        source_context=source_context,
        parent_keyword_id=parent_keyword_id,
        level=level,
        stable_key=key,
        generation_status="stub",
        aliases_json=json.dumps(aliases, ensure_ascii=False),
    )
    db.add(node)
    db.flush()
    return node


def _annotate_text(markdown_content: str, matches: list[KeywordMatch], document_id: int) -> str:
    ordered = sorted(matches, key=lambda item: item.start)
    output: list[str] = []
    cursor = 0
    occupied_end = 0
    for match in ordered:
        if match.start < cursor or match.start < occupied_end:
            continue
        output.append(markdown_content[cursor:match.start])
        output.append(f"[{match.raw_text}](/keywords/{match.node.id}?documentId={document_id})")
        cursor = match.end
        occupied_end = match.end
    output.append(markdown_content[cursor:])
    return "".join(output)


def _candidates_from_learning_keywords(items: list[dict], limit: int) -> list[EntityCandidate]:
    candidates: list[EntityCandidate] = []
    for item in items:
        try:
            keyword = LearningKeyword.model_validate(item)
        except Exception:
            continue
        candidate = EntityCandidate(
            text=keyword.text,
            type=keyword.type if keyword.type in {"term", "parameter", "formula"} else "term",
            normalized=keyword.normalized or normalize_text(keyword.text),
            reason=keyword.reason,
            aliases=keyword.aliases,
        )
        if _valid_candidate(candidate):
            candidates.append(candidate)
        if len(candidates) >= limit:
            break
    return candidates


def annotate_document_keywords(db: Session, document: Document) -> Document:
    settings = get_settings()
    if not document.markdown_content:
        raise HTTPException(status_code=400, detail="Document must be parsed before annotation.")

    candidates = _candidates_from_learning_keywords(document.learning_keywords, limit=settings.max_annotation_entities)
    if not candidates:
        candidates = [
            candidate
            for candidate in extract_entities_fallback(document.markdown_content)
            if _valid_candidate(candidate)
        ][: settings.max_annotation_entities]

    db.execute(delete(KeywordNode).where(KeywordNode.paper_id == document.id))
    db.commit()

    matches: list[KeywordMatch] = []
    occupied: list[tuple[int, int]] = []
    seen_normalized: set[str] = set()
    protected = _protected_ranges(document.markdown_content)

    for candidate in candidates:
        normalized = normalize_text(candidate.normalized or candidate.text)
        if normalized in seen_normalized:
            continue
        occurrence = locate_first_occurrence(document.markdown_content, candidate, protected=protected)
        if not occurrence:
            continue
        start, end, raw_text = occurrence
        if any(not (end <= existing_start or start >= existing_end) for existing_start, existing_end in occupied):
            continue

        node = _resolve_or_create_keyword_node(
            db=db,
            document=document,
            candidate=candidate,
            raw_text=raw_text,
            source_sentence=_source_sentence(document.markdown_content, start, end),
            source_context=_source_context(document.markdown_content, start, end),
            parent_keyword_id=None,
            level=1,
        )
        matches.append(KeywordMatch(node=node, raw_text=raw_text, start=start, end=end))
        occupied.append((start, end))
        seen_normalized.add(normalized)

    document.annotated_markdown = _annotate_text(document.markdown_content, matches, document_id=document.id)
    document.status = "annotated"
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def _keyword_markdown(content: KeywordExplanationContent) -> str:
    lines = [
        f"# {content.keyword}",
        "",
        "## What it means",
        content.meaning or "N/A",
        "",
        "## What it means in this paper",
        content.paper_specific_meaning or "N/A",
        "",
        "## Why this paper needs it",
        content.why_needed or "N/A",
        "",
        "## Relationship to nearby concepts",
        content.relationships or "N/A",
        "",
        "## Common misunderstandings",
    ]
    lines.extend([f"- {item}" for item in content.common_misunderstandings] or ["- N/A"])
    lines.extend(["", "## Intuitive example", content.intuitive_example or "N/A"])
    return "\n".join(lines)


def _content_from_node(node: KeywordNode) -> KeywordExplanationContent | None:
    data = node.explanation
    if not data:
        return None
    try:
        return KeywordExplanationContent.model_validate(data)
    except Exception:
        return None


def _learning_path(db: Session, node: KeywordNode) -> list[KeywordPathItem]:
    ids: list[int] = []
    current: KeywordNode | None = node
    while current:
        ids.append(current.id)
        current = current.parent
    ids.reverse()
    nodes = {item.id: item for item in db.execute(select(KeywordNode).where(KeywordNode.id.in_(ids))).scalars().all()}
    return [
        KeywordPathItem(
            id=node_id,
            keyword=nodes[node_id].keyword if node_id in nodes else str(node_id),
            keyword_type=nodes[node_id].keyword_type if node_id in nodes else "term",
            level=index + 1,
        )
        for index, node_id in enumerate(ids)
    ]


def _keyword_links_for_parent(node: KeywordNode) -> list[KeywordLink]:
    links: list[KeywordLink] = []
    for child in sorted(node.children, key=lambda item: (item.keyword.lower(), item.id)):
        links.append(
            KeywordLink(
                keyword_id=child.id,
                href=f"/keywords/{child.id}?documentId={node.paper_id}",
                raw_text=child.keyword,
                keyword=child.keyword,
                normalized_keyword=child.normalized_keyword,
                keyword_type=child.keyword_type,
                aliases=child.aliases,
            )
        )
    return links


def _detail(db: Session, node: KeywordNode) -> KeywordDetail:
    max_depth = get_settings().max_keyword_depth
    return KeywordDetail(
        id=node.id,
        paper_id=node.paper_id,
        keyword=node.keyword,
        normalized_keyword=node.normalized_keyword,
        keyword_type=node.keyword_type,
        source_sentence=node.source_sentence,
        source_context=node.source_context,
        parent_keyword_id=node.parent_keyword_id,
        level=node.level,
        max_depth=max_depth,
        depth_limit_reached=node.level >= max_depth,
        generation_status=node.generation_status,
        error_message=node.error_message,
        explanation_content=_content_from_node(node),
        annotated_markdown=node.annotated_markdown,
        keyword_links=_keyword_links_for_parent(node),
        learning_path=_learning_path(db=db, node=node),
        created_at=node.created_at,
        updated_at=node.updated_at,
    )


def _get_keyword_node(db: Session, keyword_id: int) -> KeywordNode:
    node = (
        db.execute(
            select(KeywordNode)
            .where(KeywordNode.id == keyword_id)
            .options(
                joinedload(KeywordNode.document),
                joinedload(KeywordNode.parent),
                joinedload(KeywordNode.children),
            )
        )
        .unique()
        .scalar_one_or_none()
    )
    if not node:
        raise HTTPException(status_code=404, detail="Keyword not found.")
    return node


def _create_child_keywords(db: Session, node: KeywordNode, content: KeywordExplanationContent, markdown: str) -> list[KeywordMatch]:
    if node.level >= get_settings().max_keyword_depth:
        return []
    document = node.document
    protected = _protected_ranges(markdown)
    occupied: list[tuple[int, int]] = []
    matches: list[KeywordMatch] = []
    seen: set[str] = set()
    candidates = [
        EntityCandidate(
            text=item.text,
            type=item.type if item.type in {"term", "parameter", "formula"} else "term",
            normalized=item.normalized or normalize_text(item.text),
            reason=item.reason,
            aliases=item.aliases,
        )
        for item in content.learning_keywords
    ]
    if not candidates:
        candidates = extract_entities_fallback(markdown)

    for candidate in candidates:
        if not _valid_candidate(candidate, current_keyword=node.keyword):
            continue
        normalized = normalize_text(candidate.normalized or candidate.text)
        if normalized in seen:
            continue
        occurrence = locate_first_occurrence(markdown, candidate, protected=protected)
        if not occurrence:
            continue
        start, end, raw_text = occurrence
        if any(not (end <= existing_start or start >= existing_end) for existing_start, existing_end in occupied):
            continue
        local_sentence = _source_sentence(markdown, start, end)
        local_context = _source_context(markdown, start, end)
        child_context = "\n\n".join(
            item
            for item in [
                f"Parent keyword: {node.keyword}",
                f"Parent source context from paper: {node.source_context or ''}",
                f"Local context from generated note: {local_context}",
            ]
            if item
        )
        child = _resolve_or_create_keyword_node(
            db=db,
            document=document,
            candidate=candidate,
            raw_text=raw_text,
            source_sentence=local_sentence,
            source_context=child_context[:2200],
            parent_keyword_id=node.id,
            level=node.level + 1,
        )
        matches.append(KeywordMatch(node=child, raw_text=raw_text, start=start, end=end))
        occupied.append((start, end))
        seen.add(normalized)
        if len(matches) >= get_settings().max_annotation_entities:
            break
    return matches


def _generate_keyword_node(db: Session, node: KeywordNode, force: bool = False) -> KeywordNode:
    if node.generation_status == "generated" and node.explanation_content and not force:
        return node
    if node.generation_status == "error" and not force:
        return node

    max_depth = get_settings().max_keyword_depth
    node.generation_status = "generating"
    node.error_message = None
    db.add(node)
    db.commit()
    db.refresh(node)

    try:
        path = " > ".join(item.keyword for item in _learning_path(db=db, node=node))
        sections = llm_service.generate_keyword_page(
            keyword=node.keyword,
            keyword_type=node.keyword_type,
            source_sentence=node.source_sentence or node.keyword,
            source_context=node.source_context or node.keyword,
            paper_title=node.document.title if node.document else "",
            learning_path=path,
            level=node.level,
            max_depth=max_depth,
            output_language=node.document.preferred_language if node.document else "zh",
        )
        content = KeywordExplanationContent(
            keyword=node.keyword,
            keyword_type=node.keyword_type,
            meaning=sections.meaning,
            paper_specific_meaning=sections.paper_specific_meaning,
            why_needed=sections.why_needed,
            relationships=sections.relationships,
            common_misunderstandings=sections.common_misunderstandings[:4],
            intuitive_example=sections.intuitive_example,
            learning_keywords=sections.learning_keywords,
            level=node.level,
            max_depth=max_depth,
            depth_limit_reached=node.level >= max_depth,
        )
        markdown = _keyword_markdown(content)
        child_matches = _create_child_keywords(db=db, node=node, content=content, markdown=markdown)
        annotated = _annotate_text(markdown, child_matches, document_id=node.paper_id) if child_matches else markdown
        node.explanation_content = content.model_dump_json()
        node.annotated_markdown = annotated
        node.generation_status = "generated"
        node.error_message = None
    except LLMGenerationError as exc:
        node.generation_status = "error"
        node.error_message = str(exc)
    except Exception as exc:
        node.generation_status = "error"
        node.error_message = f"Unexpected keyword generation failure: {exc}"

    db.add(node)
    db.commit()
    return _get_keyword_node(db=db, keyword_id=node.id)


def get_keyword_detail(db: Session, keyword_id: int) -> KeywordDetail:
    node = _get_keyword_node(db=db, keyword_id=keyword_id)
    if node.generation_status in {"stub", "generating"}:
        node = _generate_keyword_node(db=db, node=node)
    return _detail(db=db, node=node)


def retry_keyword_generation(db: Session, keyword_id: int) -> KeywordDetail:
    node = _get_keyword_node(db=db, keyword_id=keyword_id)
    node = _generate_keyword_node(db=db, node=node, force=True)
    return _detail(db=db, node=node)
