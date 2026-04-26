from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.llm import ConceptPageContent


ConceptStatus = Literal["unknown", "learning", "mastered"]


class MasteredConceptItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_name: str
    concept_type: str
    short_explanation: str | None = None
    updated_at: datetime | None = None


class MasteredConceptListResponse(BaseModel):
    items: list[MasteredConceptItem]


class ConceptStateRequest(BaseModel):
    status: ConceptStatus


class ConceptStateResponse(BaseModel):
    concept_id: int
    status: ConceptStatus


class ConceptRelationItem(BaseModel):
    id: int
    canonical_name: str
    concept_type: str
    relation_type: str
    aliases: list[str] = []


class ConceptPathItem(BaseModel):
    id: int
    canonical_name: str
    concept_type: str
    depth: int


class ConceptDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    canonical_name: str
    concept_type: str
    short_explanation: str | None = None
    long_explanation: str | None = None
    prerequisites_json: str | None = None
    output_language: str
    state: ConceptStatus
    concept_page_markdown: str
    concept_page: ConceptPageContent | None = None
    related_document_ids: list[int]
    prerequisites: list[ConceptRelationItem]
    learning_path: list[ConceptPathItem] = []
    depth_limit_reached: bool = False
    created_at: datetime
    updated_at: datetime | None = None


class ConceptExpandResponse(BaseModel):
    concept_id: int
    expanded: bool
    added_concept_ids: list[int]
    concept_page_markdown: str
    concept_page: ConceptPageContent | None = None
    depth_limit_reached: bool = False
