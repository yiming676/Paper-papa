from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_db
from app.schemas.document import DocumentSummary
from app.services.document_service import save_uploaded_pdf

router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentSummary,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    file: UploadFile = File(...),
    preferred_language: str = Form("en"),
    db: Session = Depends(get_db),
) -> DocumentSummary:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    if preferred_language not in {"en", "zh"}:
        raise HTTPException(status_code=400, detail="preferred_language must be 'en' or 'zh'.")

    document = await save_uploaded_pdf(db=db, file=file, preferred_language=preferred_language)
    return DocumentSummary.model_validate(document)
