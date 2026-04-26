import re
from pathlib import Path

import fitz

from app.schemas.llm import PaperAsset, PaperReference


def _clean_text(value: str, limit: int = 1200) -> str:
    return " ".join(value.split())[:limit]


def _reference_label(raw: str, number: str) -> tuple[str, str]:
    lowered = raw.lower()
    if lowered.startswith(("table", "tab")) or raw.startswith("表"):
        return "table", f"Table {number}"
    return "figure", f"Figure {number}"


def _extract_reference_candidates(page_text: str, page: int, limit: int = 12) -> list[PaperReference]:
    references: list[PaperReference] = []
    seen: set[tuple[str, str]] = set()
    pattern = re.compile(
        r"\b(?P<label>Figure|Fig\.?|Table|Tab\.?)\s*(?P<number>\d+(?:\.\d+)?)[\.:]?\s*(?P<body>[^\n]{0,360})"
        r"|(?P<cjk_label>[图表])\s*(?P<cjk_number>\d+(?:\.\d+)?)[：:\.]?\s*(?P<cjk_body>[^\n]{0,360})",
        flags=re.IGNORECASE,
    )

    for match in pattern.finditer(page_text):
        raw_label = match.group("label") or match.group("cjk_label") or ""
        number = match.group("number") or match.group("cjk_number") or ""
        body = match.group("body") or match.group("cjk_body") or ""
        reference_type, label = _reference_label(raw_label, number)
        key = (reference_type, label)
        if key in seen:
            continue
        seen.add(key)
        start = max(0, match.start() - 240)
        end = min(len(page_text), match.end() + 360)
        references.append(
            PaperReference(
                type=reference_type,
                label=label,
                page=page,
                caption=_clean_text(body, limit=360) or None,
                context=_clean_text(page_text[start:end], limit=800),
            )
        )
        if len(references) >= limit:
            break

    return references


def extract_text_from_pdf(file_path: str | Path) -> str:
    document = fitz.open(file_path)
    pages: list[str] = []
    for page in document:
        pages.append(page.get_text("text"))
    document.close()
    return "\n".join(pages).strip()


def extract_paper_content(
    file_path: str | Path,
    document_id: int,
    assets_root: str | Path,
    max_references: int = 20,
) -> tuple[str, list[PaperReference], list[PaperAsset]]:
    pdf = fitz.open(file_path)
    pages: list[str] = []
    references: list[PaperReference] = []
    seen: set[tuple[str, str]] = set()

    for page_index, page in enumerate(pdf, start=1):
        page_text = page.get_text("text")
        pages.append(page_text)
        if len(references) >= max_references:
            continue
        for reference in _extract_reference_candidates(page_text, page=page_index):
            key = (reference.type, reference.label)
            if key in seen:
                continue
            seen.add(key)
            references.append(reference)
            if len(references) >= max_references:
                break

    pdf.close()
    return "\n".join(pages).strip(), references, []
