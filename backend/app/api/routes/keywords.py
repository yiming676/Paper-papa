from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, status

from app.api.deps import get_db
from app.schemas.keyword import KeywordDetail
from app.services.keyword_service import get_keyword_detail, retry_keyword_generation

router = APIRouter()


@router.get(
    "/{keyword_id}",
    response_model=KeywordDetail,
    status_code=status.HTTP_200_OK,
)
def get_keyword(
    keyword_id: int,
    document_id: int | None = None,
    db: Session = Depends(get_db),
) -> KeywordDetail:
    return get_keyword_detail(db=db, keyword_id=keyword_id)


@router.post(
    "/{keyword_id}/retry",
    response_model=KeywordDetail,
    status_code=status.HTTP_200_OK,
)
def retry_keyword(
    keyword_id: int,
    document_id: int | None = None,
    db: Session = Depends(get_db),
) -> KeywordDetail:
    return retry_keyword_generation(db=db, keyword_id=keyword_id)
