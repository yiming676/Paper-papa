import json
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_file: Mapped[str] = mapped_column(String(500), nullable=False)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotated_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    study_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    asset_manifest_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="uploaded")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    entities: Mapped[list["DocumentEntity"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
    )

    @property
    def study_report(self) -> dict | None:
        if not self.study_report_json:
            return None
        try:
            return json.loads(self.study_report_json)
        except json.JSONDecodeError:
            return None

    @property
    def asset_manifest(self) -> list[dict]:
        if not self.asset_manifest_json:
            return []
        try:
            value = json.loads(self.asset_manifest_json)
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    @property
    def learning_keywords(self) -> list[dict]:
        report = self.study_report
        if not isinstance(report, dict):
            return []
        keywords = report.get("learning_keywords")
        return keywords if isinstance(keywords, list) else []

    @property
    def concept_links(self) -> list[dict]:
        links: list[dict] = []
        for entity in sorted(self.entities, key=lambda item: item.position_start):
            concept = entity.concept
            aliases = concept.aliases if concept else []
            links.append(
                {
                    "concept_id": entity.concept_id,
                    "href": f"/concepts/{entity.concept_id}?documentId={self.id}",
                    "raw_text": entity.raw_text,
                    "canonical_name": concept.canonical_name if concept else entity.raw_text,
                    "normalized_text": entity.normalized_text,
                    "entity_type": entity.entity_type,
                    "aliases": aliases,
                }
            )
        return links


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    raw_text: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_text: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    first_occurrence_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    position_start: Mapped[int] = mapped_column(Integer, nullable=False)
    position_end: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="entities")
    concept: Mapped["Concept"] = relationship(back_populates="document_entities")
