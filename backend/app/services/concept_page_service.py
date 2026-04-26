from app.models.concept import Concept
from app.schemas.llm import ConceptPageContent, ConceptPageSections
from app.core.config import get_settings


def get_section_labels(output_language: str) -> dict[str, str]:
    if output_language == "zh":
        return {
            "one_line_explanation": "一句话解释",
            "intuition": "直觉理解",
            "role_in_this_paper": "在本文中的作用",
            "strict_definition": "严格定义",
            "prerequisites": "前置概念",
            "example": "示例",
            "none": "暂无",
        }
    return {
        "one_line_explanation": "One-line explanation",
        "intuition": "Intuition",
        "role_in_this_paper": "Role in this paper",
        "strict_definition": "Strict definition",
        "prerequisites": "Prerequisites",
        "example": "Example",
        "none": "None",
    }


def build_concept_content(
    concept: Concept,
    sections: ConceptPageSections,
    output_language: str,
    depth: int = 1,
    depth_limit_reached: bool = False,
) -> ConceptPageContent:
    aliases: list[str] = []
    if concept.normalized_name and concept.normalized_name != concept.canonical_name.lower():
        aliases.append(concept.normalized_name)
    return ConceptPageContent(
        title=concept.canonical_name,
        concept_type=concept.concept_type,
        aliases=aliases,
        one_line_explanation=sections.one_line_explanation,
        intuition=sections.intuition,
        role_in_this_paper=sections.role_in_this_paper,
        strict_definition=sections.strict_definition,
        prerequisites=sections.prerequisites[:5],
        example=sections.example,
        depth=depth,
        max_depth=get_settings().max_expand_depth,
        depth_limit_reached=depth_limit_reached,
    )


def build_concept_markdown(
    concept: Concept,
    sections: ConceptPageSections,
    output_language: str,
    linked_prerequisites: list[tuple[int, str]] | None = None,
    document_id: int | None = None,
    depth_limit_reached: bool = False,
) -> str:
    labels = get_section_labels(output_language)
    link_suffix = f"?documentId={document_id}" if document_id is not None else ""

    prerequisite_lines: list[str] = []
    if linked_prerequisites:
        prerequisite_lines.extend(
            [f"- [{name}](/concepts/{concept_id}{link_suffix})" for concept_id, name in linked_prerequisites]
        )
    elif sections.prerequisites:
        prerequisite_lines.extend([f"- {item}" for item in sections.prerequisites[:5]])
    else:
        prerequisite_lines.append(f"- {labels['none']}")

    if depth_limit_reached:
        prerequisite_lines.append(
            "- 已到递归上限，后续概念不会继续自动展开。"
            if output_language == "zh"
            else "- Recursion depth limit reached; this branch will not expand further."
        )

    return "\n".join(
        [
            f"# {concept.canonical_name}",
            "",
            f"## {labels['one_line_explanation']}",
            sections.one_line_explanation,
            "",
            f"## {labels['intuition']}",
            sections.intuition,
            "",
            f"## {labels['role_in_this_paper']}",
            sections.role_in_this_paper,
            "",
            f"## {labels['strict_definition']}",
            sections.strict_definition,
            "",
            f"## {labels['prerequisites']}",
            *prerequisite_lines,
            "",
            f"## {labels['example']}",
            sections.example,
        ]
    )
