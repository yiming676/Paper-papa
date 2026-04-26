import re
import shutil
import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.services.llm_service import LLMGenerationError, llm_service
from app.services.heuristics import study_report_to_markdown
from app.services.pdf_service import extract_paper_content


def _sanitize_filename(filename: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", filename)
    return safe or "paper.pdf"


async def save_uploaded_pdf(db: Session, file: UploadFile, preferred_language: str = "en") -> Document:
    settings = get_settings()
    upload_dir = Path(settings.storage_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)

    safe_name = _sanitize_filename(file.filename or "paper.pdf")
    destination = upload_dir / f"{uuid4().hex}_{safe_name}"
    with destination.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    title = Path(safe_name).stem.replace("_", " ").strip() or "Untitled Paper"
    document = Document(
        title=title,
        source_file=str(destination),
        preferred_language=preferred_language,
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


def get_document_or_404(db: Session, document_id: int) -> Document:
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return document


def _looks_like_chinese_text(text: str) -> bool:
    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", text))
    latin_words = len(re.findall(r"\b[a-zA-Z]{3,}\b", text))
    return cjk_count > 20 and cjk_count >= latin_words


def _document_report_text(document: Document) -> str:
    report = document.study_report
    if not isinstance(report, dict):
        return ""
    pieces: list[str] = []
    for key in [
        "core_insight",
        "problem_and_motivation",
        "core_innovations",
        "data_representation",
        "architecture_highlights",
        "limitations",
        "reading_checklist",
        "warnings",
    ]:
        value = report.get(key)
        if isinstance(value, str):
            pieces.append(value)
        elif isinstance(value, list):
            pieces.extend(str(item) for item in value)
    return "\n".join(pieces)


def ensure_document_display_language(db: Session, document: Document) -> Document:
    return document


def parse_document(db: Session, document_id: int) -> Document:
    document = get_document_or_404(db=db, document_id=document_id)
    settings = get_settings()
    raw_text, paper_references, assets = extract_paper_content(
        document.source_file,
        document_id=document.id,
        assets_root=settings.assets_dir,
    )
    if not raw_text:
        raise HTTPException(status_code=400, detail="Could not extract text from the PDF.")

    try:
        report = llm_service.generate_study_report(
            raw_text=raw_text,
            title=document.title,
            output_language=document.preferred_language,
            paper_references=paper_references,
            assets=assets,
        )
    except LLMGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "LLM API failed to generate the study report. "
                "Check OPENAI_API_KEY, OPENAI_BASE_URL, MODEL_NAME, and provider response format. "
                f"Reason: {exc}"
            ),
        ) from exc
    markdown = study_report_to_markdown(report, output_language=document.preferred_language)
    document.raw_text = raw_text
    document.markdown_content = markdown
    document.study_report_json = report.model_dump_json()
    document.asset_manifest_json = json.dumps([asset.model_dump() for asset in assets], ensure_ascii=False)
    document.status = "parsed"
    db.add(document)
    db.commit()
    db.refresh(document)
    return document
