from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.llm import LearningKeyword, PaperAsset, StudyReport


class DocumentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_file: str
    preferred_language: str
    status: str
    created_at: datetime
    updated_at: datetime | None = None


class DocumentSummary(DocumentBase):
    pass


class DocumentConceptLink(BaseModel):
    concept_id: int
    href: str
    raw_text: str
    canonical_name: str
    normalized_text: str
    entity_type: str
    aliases: list[str] = []


class DocumentDetail(DocumentBase):
    raw_text: str | None = None
    markdown_content: str | None = None
    annotated_markdown: str | None = None
    study_report: StudyReport | None = None
    asset_manifest: list[PaperAsset] = []
    learning_keywords: list[LearningKeyword] = []
    concept_links: list[DocumentConceptLink] = []
