import json
from collections import deque

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.normalization import normalize_text
from app.models.concept import Concept, ConceptPage, ConceptRelation, UserConceptState
from app.models.document import Document, DocumentEntity
from app.schemas.concept import (
    ConceptDetail,
    ConceptExpandResponse,
    ConceptPathItem,
    ConceptRelationItem,
    ConceptStateResponse,
    MasteredConceptItem,
)
from app.schemas.llm import ConceptPageContent, ConceptPageSections
from app.services.concept_page_service import build_concept_content, build_concept_markdown, get_section_labels
from app.services.llm_service import llm_service


GENERIC_PREREQUISITES = {"method", "model", "data", "dataset", "paper", "result", "experiment", "approach", "task"}


def _extract_markdown_section(markdown_content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = markdown_content.find(marker)
    if start < 0:
        return ""

    content_start = start + len(marker)
    remainder = markdown_content[content_start:].lstrip("\n")
    next_heading = remainder.find("\n## ")
    if next_heading < 0:
        return remainder.strip()
    return remainder[:next_heading].strip()


def _get_concept(db: Session, concept_id: int) -> Concept:
    statement = (
        select(Concept)
        .where(Concept.id == concept_id)
        .options(
            joinedload(Concept.pages),
            joinedload(Concept.state),
            joinedload(Concept.parent_relations).joinedload(ConceptRelation.child_concept),
            joinedload(Concept.child_relations).joinedload(ConceptRelation.parent_concept),
            joinedload(Concept.document_entities),
        )
    )
    concept = db.execute(statement).unique().scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found.")
    if not concept.normalized_name:
        concept.normalized_name = normalize_text(concept.canonical_name)
        db.add(concept)
        db.flush()
    return concept


def _build_context_snippet(db: Session, concept: Concept) -> str:
    entity = db.execute(
        select(DocumentEntity)
        .where(DocumentEntity.concept_id == concept.id)
        .order_by(DocumentEntity.created_at.asc())
    ).scalars().first()
    if not entity:
        return concept.canonical_name

    document = db.get(Document, entity.document_id)
    if not document:
        return entity.raw_text

    source = document.markdown_content or document.raw_text or ""
    if not source:
        return entity.raw_text

    index = source.lower().find(entity.raw_text.lower())
    if index < 0:
        local_context = source[:1000]
    else:
        start = max(0, index - 450)
        end = min(len(source), index + len(entity.raw_text) + 650)
        local_context = source[start:end]

    report = document.study_report if isinstance(document.study_report, dict) else {}
    references = report.get("paper_references") if isinstance(report, dict) else []
    reference_lines: list[str] = []
    if isinstance(references, list):
        for reference in references[:6]:
            if not isinstance(reference, dict):
                continue
            label = reference.get("label") or ""
            page = f" p.{reference.get('page')}" if reference.get("page") else ""
            reason = reference.get("reason") or reference.get("caption") or reference.get("context") or ""
            if label:
                reference_lines.append(f"- {label}{page}: {reason}")

    path_names = " -> ".join(item.canonical_name for item in _learning_path(db=db, concept=concept))
    return "\n".join(
        item
        for item in [
            f"论文标题：{document.title}",
            f"当前点击概念：{concept.canonical_name}",
            f"概念层级路径：{path_names}" if path_names else "",
            f"概念首次出现文本：{entity.raw_text}",
            "首次出现附近上下文：",
            local_context,
            "论文图表引用线索（仅用于提示用户回原文查看）：",
            "\n".join(reference_lines),
        ]
        if item
    )


def _resolve_concept_language(db: Session, concept: Concept, document_id: int | None = None) -> str:
    if document_id is not None:
        document = db.get(Document, document_id)
        if document and getattr(document, "preferred_language", None):
            return document.preferred_language

    entity = db.execute(
        select(DocumentEntity)
        .where(DocumentEntity.concept_id == concept.id)
        .order_by(DocumentEntity.created_at.asc())
    ).scalars().first()
    if not entity:
        return "en"

    document = db.get(Document, entity.document_id)
    if not document or not getattr(document, "preferred_language", None):
        return "en"
    return document.preferred_language


def _get_latest_page_for_language(db: Session, concept_id: int, output_language: str) -> ConceptPage | None:
    return db.execute(
        select(ConceptPage)
        .where(
            ConceptPage.concept_id == concept_id,
            ConceptPage.language == output_language,
        )
        .order_by(ConceptPage.version.desc())
    ).scalars().first()


def _content_from_page(page: ConceptPage | None) -> ConceptPageContent | None:
    if not page or not page.content:
        return None
    try:
        return ConceptPageContent.model_validate(page.content)
    except Exception:
        return None


def _concept_depth(db: Session, concept_id: int) -> int:
    roots = {row[0] for row in db.execute(select(DocumentEntity.concept_id).distinct()).all()}
    if concept_id in roots:
        return 1

    graph = db.execute(select(ConceptRelation.parent_concept_id, ConceptRelation.child_concept_id)).all()
    parents_by_child: dict[int, list[int]] = {}
    for parent_id, child_id in graph:
        parents_by_child.setdefault(child_id, []).append(parent_id)

    queue = deque([(concept_id, 1)])
    visited = {concept_id}
    min_depth = 99
    while queue:
        current_id, depth = queue.popleft()
        if current_id in roots:
            min_depth = min(min_depth, depth)
        for parent_id in parents_by_child.get(current_id, []):
            if parent_id not in visited:
                visited.add(parent_id)
                queue.append((parent_id, depth + 1))
    return min_depth if min_depth != 99 else 1


def _depth_limit_reached(db: Session, concept_id: int) -> bool:
    return _concept_depth(db=db, concept_id=concept_id) >= get_settings().max_expand_depth


def _would_create_cycle(db: Session, parent_id: int, child_id: int) -> bool:
    if parent_id == child_id:
        return True

    edges = db.execute(select(ConceptRelation.parent_concept_id, ConceptRelation.child_concept_id)).all()
    children_by_parent: dict[int, list[int]] = {}
    for existing_parent_id, existing_child_id in edges:
        children_by_parent.setdefault(existing_parent_id, []).append(existing_child_id)

    queue = deque([child_id])
    visited = {child_id}
    while queue:
        current_id = queue.popleft()
        if current_id == parent_id:
            return True
        for next_id in children_by_parent.get(current_id, []):
            if next_id not in visited:
                visited.add(next_id)
                queue.append(next_id)
    return False


def _learning_path(db: Session, concept: Concept) -> list[ConceptPathItem]:
    roots = {row[0] for row in db.execute(select(DocumentEntity.concept_id).distinct()).all()}
    if concept.id in roots:
        return [ConceptPathItem(id=concept.id, canonical_name=concept.canonical_name, concept_type=concept.concept_type, depth=1)]

    relations = db.execute(select(ConceptRelation.parent_concept_id, ConceptRelation.child_concept_id)).all()
    parents_by_child: dict[int, list[int]] = {}
    for parent_id, child_id in relations:
        parents_by_child.setdefault(child_id, []).append(parent_id)

    queue = deque([(concept.id, [concept.id])])
    visited = {concept.id}
    best_path = [concept.id]
    while queue:
        current_id, path = queue.popleft()
        if current_id in roots:
            best_path = list(reversed(path))
            break
        for parent_id in parents_by_child.get(current_id, []):
            if parent_id not in visited:
                visited.add(parent_id)
                queue.append((parent_id, path + [parent_id]))

    concepts = {
        item.id: item
        for item in db.execute(select(Concept).where(Concept.id.in_(best_path))).scalars().all()
    }
    return [
        ConceptPathItem(
            id=concept_id,
            canonical_name=concepts.get(concept_id).canonical_name if concepts.get(concept_id) else str(concept_id),
            concept_type=concepts.get(concept_id).concept_type if concepts.get(concept_id) else "term",
            depth=index + 1,
        )
        for index, concept_id in enumerate(best_path)
    ]


def _sections_from_page(
    concept: Concept,
    page: ConceptPage,
    prerequisite_names: list[str],
    output_language: str,
) -> ConceptPageSections:
    content = _content_from_page(page)
    if content:
        return ConceptPageSections(
            one_line_explanation=content.one_line_explanation,
            intuition=content.intuition,
            role_in_this_paper=content.role_in_this_paper,
            strict_definition=content.strict_definition,
            prerequisites=prerequisite_names or content.prerequisites,
            example=content.example,
        )

    labels = get_section_labels(output_language)
    if output_language == "zh":
        one_line_fallback = concept.short_explanation or f"{concept.canonical_name} 是当前论文学习链条中的一个概念。"
        intuition_fallback = f"{concept.canonical_name} 可以理解为本文推理链中的一个局部知识支点。"
        role_fallback = concept.long_explanation or f"{concept.canonical_name} 在当前论文中承担方法说明、假设解释或公式说明的作用。"
        definition_fallback = concept.long_explanation or f"{concept.canonical_name} 的定义应结合当前论文语境理解。"
        example_fallback = f"回到论文中 {concept.canonical_name} 首次出现的位置，可以看到它在本文中的具体用法。"
    else:
        one_line_fallback = concept.short_explanation or f"{concept.canonical_name} is a concept used in the paper."
        intuition_fallback = f"{concept.canonical_name} can be understood as one local knowledge unit in the paper's reasoning chain."
        role_fallback = concept.long_explanation or f"{concept.canonical_name} matters because it appears in the current paper context."
        definition_fallback = concept.long_explanation or f"{concept.canonical_name} is defined here according to its role in the paper."
        example_fallback = f"Return to the document passage where {concept.canonical_name} first appears to see the paper-specific usage."

    return ConceptPageSections(
        one_line_explanation=_extract_markdown_section(page.markdown_content, labels["one_line_explanation"]) or one_line_fallback,
        intuition=_extract_markdown_section(page.markdown_content, labels["intuition"]) or intuition_fallback,
        role_in_this_paper=_extract_markdown_section(page.markdown_content, labels["role_in_this_paper"]) or role_fallback,
        strict_definition=_extract_markdown_section(page.markdown_content, labels["strict_definition"]) or definition_fallback,
        prerequisites=prerequisite_names,
        example=_extract_markdown_section(page.markdown_content, labels["example"]) or example_fallback,
    )


def _ensure_concept_page(
    db: Session,
    concept: Concept,
    output_language: str,
    document_id: int | None = None,
) -> ConceptPage:
    existing_page = _get_latest_page_for_language(db=db, concept_id=concept.id, output_language=output_language)
    if existing_page and _content_from_page(existing_page) and concept.generation_status == "generated":
        return existing_page

    context_snippet = _build_context_snippet(db=db, concept=concept)
    sections = llm_service.generate_concept_page(
        concept_name=concept.canonical_name,
        concept_type=concept.concept_type,
        context_snippet=context_snippet,
        output_language=output_language,
    )
    depth = _concept_depth(db=db, concept_id=concept.id)
    depth_limit_reached = depth >= get_settings().max_expand_depth
    content = build_concept_content(
        concept=concept,
        sections=sections,
        output_language=output_language,
        depth=depth,
        depth_limit_reached=depth_limit_reached,
    )

    concept.normalized_name = concept.normalized_name or normalize_text(concept.canonical_name)
    concept.generation_status = "generated"
    concept.long_explanation = sections.strict_definition
    concept.prerequisites_json = json.dumps(sections.prerequisites[: get_settings().max_prerequisites_per_concept], ensure_ascii=False)
    page = ConceptPage(
        concept_id=concept.id,
        language=output_language,
        markdown_content=build_concept_markdown(
            concept,
            sections,
            output_language=output_language,
            document_id=document_id,
            depth_limit_reached=depth_limit_reached,
        ),
        content_json=content.model_dump_json(),
        version=(existing_page.version + 1) if existing_page else 1,
    )
    db.add(page)
    db.add(concept)
    db.commit()
    db.refresh(page)
    return page


def _resolve_or_create_prerequisite(
    db: Session,
    name: str,
    output_language: str,
) -> Concept:
    normalized = normalize_text(name)
    concept = db.execute(
        select(Concept).where(
            Concept.concept_type == "term",
            Concept.normalized_name == normalized,
        )
    ).scalar_one_or_none()
    if concept:
        merged_aliases = sorted({*concept.aliases, normalized} - {concept.canonical_name, ""})
        concept.aliases_json = json.dumps(merged_aliases, ensure_ascii=False)
        db.add(concept)
        return concept

    concept = db.execute(select(Concept).where(Concept.canonical_name.ilike(name))).scalar_one_or_none()
    if concept:
        if not concept.normalized_name:
            concept.normalized_name = normalized
        merged_aliases = sorted({*concept.aliases, normalized} - {concept.canonical_name, ""})
        concept.aliases_json = json.dumps(merged_aliases, ensure_ascii=False)
        db.add(concept)
        db.flush()
        return concept

    concept = Concept(
        canonical_name=name.strip(),
        normalized_name=normalized,
        concept_type="term",
        generation_status="stub",
        short_explanation="前置概念" if output_language == "zh" else "Prerequisite concept",
        aliases_json=json.dumps([normalized] if normalized != name.strip() else [], ensure_ascii=False),
    )
    db.add(concept)
    db.flush()
    db.add(UserConceptState(concept_id=concept.id, status="unknown"))
    db.flush()
    return concept


def _valid_prerequisite_name(parent: Concept, name: str) -> bool:
    normalized = normalize_text(name)
    if not normalized or normalized in GENERIC_PREREQUISITES:
        return False
    if normalized == (parent.normalized_name or normalize_text(parent.canonical_name)):
        return False
    return True


def _expand_concept_page(
    db: Session,
    concept: Concept,
    page: ConceptPage,
    output_language: str,
    document_id: int | None = None,
) -> ConceptExpandResponse:
    settings = get_settings()
    current_depth = _concept_depth(db=db, concept_id=concept.id)
    if current_depth >= settings.max_expand_depth:
        content = _content_from_page(page)
        return ConceptExpandResponse(
            concept_id=concept.id,
            expanded=False,
            added_concept_ids=[],
            concept_page_markdown=page.markdown_content,
            concept_page=content,
            depth_limit_reached=True,
        )

    content = _content_from_page(page)
    prerequisite_names = content.prerequisites if content else []
    if not prerequisite_names:
        prerequisite_names = llm_service.extract_recursive_prerequisites(page.markdown_content, output_language=output_language)
    prerequisite_names = [item for item in prerequisite_names if _valid_prerequisite_name(concept, item)][: settings.max_prerequisites_per_concept]

    if not prerequisite_names:
        return ConceptExpandResponse(
            concept_id=concept.id,
            expanded=False,
            added_concept_ids=[],
            concept_page_markdown=page.markdown_content,
            concept_page=content,
            depth_limit_reached=False,
        )

    added_ids: list[int] = []
    linked_prerequisites: list[tuple[int, str]] = []

    for item in prerequisite_names:
        child_concept = _resolve_or_create_prerequisite(
            db=db,
            name=item,
            output_language=output_language,
        )
        if _would_create_cycle(db=db, parent_id=concept.id, child_id=child_concept.id):
            continue

        linked_prerequisites.append((child_concept.id, child_concept.canonical_name))
        exists = db.execute(
            select(ConceptRelation).where(
                ConceptRelation.parent_concept_id == concept.id,
                ConceptRelation.child_concept_id == child_concept.id,
                ConceptRelation.relation_type == "prerequisite",
            )
        ).scalar_one_or_none()
        if not exists:
            db.add(
                ConceptRelation(
                    parent_concept_id=concept.id,
                    child_concept_id=child_concept.id,
                    relation_type="prerequisite",
                )
            )
            added_ids.append(child_concept.id)

    sections = _sections_from_page(
        concept=concept,
        page=page,
        prerequisite_names=[name for _, name in linked_prerequisites],
        output_language=output_language,
    )
    next_depth_limit = current_depth >= settings.max_expand_depth
    next_content = build_concept_content(
        concept=concept,
        sections=sections,
        output_language=output_language,
        depth=current_depth,
        depth_limit_reached=next_depth_limit,
    )
    concept.prerequisites_json = json.dumps(sections.prerequisites, ensure_ascii=False)
    next_page = ConceptPage(
        concept_id=concept.id,
        language=output_language,
        markdown_content=build_concept_markdown(
            concept,
            sections,
            output_language=output_language,
            linked_prerequisites=linked_prerequisites,
            document_id=document_id,
            depth_limit_reached=next_depth_limit,
        ),
        content_json=next_content.model_dump_json(),
        version=page.version + 1,
    )
    db.add(concept)
    db.add(next_page)
    db.commit()
    db.refresh(next_page)
    return ConceptExpandResponse(
        concept_id=concept.id,
        expanded=bool(linked_prerequisites),
        added_concept_ids=added_ids,
        concept_page_markdown=next_page.markdown_content,
        concept_page=next_content,
        depth_limit_reached=next_depth_limit,
    )


def get_concept_detail(db: Session, concept_id: int, document_id: int | None = None) -> ConceptDetail:
    concept = _get_concept(db=db, concept_id=concept_id)
    output_language = _resolve_concept_language(db=db, concept=concept, document_id=document_id)
    page = _ensure_concept_page(db=db, concept=concept, output_language=output_language, document_id=document_id)

    current_depth = _concept_depth(db=db, concept_id=concept.id)
    existing_links = [
        relation
        for relation in concept.parent_relations
        if relation.relation_type == "prerequisite"
    ]
    if not existing_links and current_depth < get_settings().max_expand_depth:
        _expand_concept_page(
            db=db,
            concept=concept,
            page=page,
            output_language=output_language,
            document_id=document_id,
        )
        page = _get_latest_page_for_language(db=db, concept_id=concept.id, output_language=output_language) or page
        concept = _get_concept(db=db, concept_id=concept_id)

    concept_page = _content_from_page(page)
    prerequisites = [
        ConceptRelationItem(
            id=relation.child_concept.id,
            canonical_name=relation.child_concept.canonical_name,
            concept_type=relation.child_concept.concept_type,
            relation_type=relation.relation_type,
            aliases=relation.child_concept.aliases,
        )
        for relation in concept.parent_relations
        if relation.relation_type == "prerequisite"
    ]
    related_document_ids = sorted({entity.document_id for entity in concept.document_entities})
    state = concept.state.status if concept.state else "unknown"
    depth_limit_reached = _depth_limit_reached(db=db, concept_id=concept.id)
    return ConceptDetail(
        id=concept.id,
        canonical_name=concept.canonical_name,
        concept_type=concept.concept_type,
        short_explanation=concept.short_explanation,
        long_explanation=concept.long_explanation,
        prerequisites_json=concept.prerequisites_json,
        output_language=output_language,
        state=state,
        concept_page_markdown=page.markdown_content,
        concept_page=concept_page,
        related_document_ids=related_document_ids,
        prerequisites=prerequisites,
        learning_path=_learning_path(db=db, concept=concept),
        depth_limit_reached=depth_limit_reached,
        created_at=concept.created_at,
        updated_at=concept.updated_at,
    )


def expand_concept(db: Session, concept_id: int, document_id: int | None = None) -> ConceptExpandResponse:
    concept = _get_concept(db=db, concept_id=concept_id)
    output_language = _resolve_concept_language(db=db, concept=concept, document_id=document_id)
    page = _ensure_concept_page(db=db, concept=concept, output_language=output_language, document_id=document_id)
    return _expand_concept_page(
        db=db,
        concept=concept,
        page=page,
        output_language=output_language,
        document_id=document_id,
    )


def set_concept_state(db: Session, concept_id: int, new_status: str) -> ConceptStateResponse:
    concept = _get_concept(db=db, concept_id=concept_id)
    if concept.state:
        concept.state.status = new_status
        db.add(concept.state)
    else:
        db.add(UserConceptState(concept_id=concept.id, status=new_status))
    db.commit()
    return ConceptStateResponse(concept_id=concept.id, status=new_status)


def list_mastered_concepts(db: Session) -> list[MasteredConceptItem]:
    statement = (
        select(Concept, UserConceptState)
        .join(UserConceptState, UserConceptState.concept_id == Concept.id)
        .where(UserConceptState.status == "mastered")
        .order_by(UserConceptState.updated_at.desc())
    )
    rows = db.execute(statement).all()
    return [
        MasteredConceptItem(
            id=concept.id,
            canonical_name=concept.canonical_name,
            concept_type=concept.concept_type,
            short_explanation=concept.short_explanation,
            updated_at=state.updated_at,
        )
        for concept, state in rows
    ]
