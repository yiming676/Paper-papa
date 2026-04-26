from sqlalchemy.orm import Session

from fastapi import APIRouter, Body, Depends, Query, status

from app.api.deps import get_db
from app.schemas.concept import (
    ConceptDetail,
    ConceptExpandResponse,
    ConceptStateRequest,
    ConceptStateResponse,
    MasteredConceptListResponse,
)
from app.services.concept_service import (
    expand_concept,
    get_concept_detail,
    list_mastered_concepts,
    set_concept_state,
)

router = APIRouter()


@router.get(
    "/mastered",
    response_model=MasteredConceptListResponse,
    status_code=status.HTTP_200_OK,
)
def get_mastered_concepts(db: Session = Depends(get_db)) -> MasteredConceptListResponse:
    items = list_mastered_concepts(db=db)
    return MasteredConceptListResponse(items=items)


@router.get(
    "/{concept_id}",
    response_model=ConceptDetail,
    status_code=status.HTTP_200_OK,
)
def get_concept(
    concept_id: int,
    document_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ConceptDetail:
    return get_concept_detail(db=db, concept_id=concept_id, document_id=document_id)


@router.post(
    "/{concept_id}/expand",
    response_model=ConceptExpandResponse,
    status_code=status.HTTP_200_OK,
)
def expand_concept_endpoint(
    concept_id: int,
    document_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> ConceptExpandResponse:
    return expand_concept(db=db, concept_id=concept_id, document_id=document_id)


@router.post(
    "/{concept_id}/state",
    response_model=ConceptStateResponse,
    status_code=status.HTTP_200_OK,
)
def update_concept_state(
    concept_id: int,
    payload: ConceptStateRequest = Body(...),
    db: Session = Depends(get_db),
) -> ConceptStateResponse:
    return set_concept_state(db=db, concept_id=concept_id, new_status=payload.status)
