from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db
from app.schemas.document import DocumentDetail, DocumentSummary
from app.services.annotation_service import annotate_document
from app.services.document_service import ensure_document_display_language, get_document_or_404, parse_document

router = APIRouter()


@router.post(
    "/{document_id}/parse",
    response_model=DocumentSummary,
    status_code=status.HTTP_200_OK,
)
def parse_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentSummary:
    document = parse_document(db=db, document_id=document_id)
    return DocumentSummary.model_validate(document)


@router.post(
    "/{document_id}/annotate",
    response_model=DocumentSummary,
    status_code=status.HTTP_200_OK,
)
def annotate_document_endpoint(
    document_id: int,
    db: Session = Depends(get_db),
) -> DocumentSummary:
    document = annotate_document(db=db, document_id=document_id)
    return DocumentSummary.model_validate(document)


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    status_code=status.HTTP_200_OK,
)
def get_document(document_id: int, db: Session = Depends(get_db)) -> DocumentDetail:
    document = get_document_or_404(db=db, document_id=document_id)
    document = ensure_document_display_language(db=db, document=document)
    return DocumentDetail.model_validate(document)
