from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.llm import LearningKeyword


KeywordGenerationStatus = Literal["stub", "generating", "generated", "error"]


class KeywordLink(BaseModel):
    keyword_id: int
    href: str
    raw_text: str
    keyword: str
    normalized_keyword: str
    keyword_type: str
    aliases: list[str] = []


class KeywordPathItem(BaseModel):
    id: int
    keyword: str
    keyword_type: str
    level: int


class KeywordExplanationContent(BaseModel):
    keyword: str
    keyword_type: str
    meaning: str = ""
    paper_specific_meaning: str = ""
    why_needed: str = ""
    relationships: str = ""
    common_misunderstandings: list[str] = Field(default_factory=list)
    intuitive_example: str = ""
    learning_keywords: list[LearningKeyword] = Field(default_factory=list)
    level: int = 1
    max_depth: int = 10
    depth_limit_reached: bool = False


class KeywordDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paper_id: int
    keyword: str
    normalized_keyword: str
    keyword_type: str
    source_sentence: str | None = None
    source_context: str | None = None
    parent_keyword_id: int | None = None
    level: int
    max_depth: int
    depth_limit_reached: bool
    generation_status: KeywordGenerationStatus
    error_message: str | None = None
    explanation_content: KeywordExplanationContent | None = None
    annotated_markdown: str | None = None
    keyword_links: list[KeywordLink] = []
    learning_path: list[KeywordPathItem] = []
    created_at: datetime
    updated_at: datetime | None = None
