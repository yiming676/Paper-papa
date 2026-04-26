import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (
        UniqueConstraint("normalized_name", "concept_type", name="uq_concepts_normalized_name_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    concept_type: Mapped[str] = mapped_column(String(50), nullable=False)
    generation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="stub")
    short_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    long_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    prerequisites_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    document_entities: Mapped[list["DocumentEntity"]] = relationship(back_populates="concept")
    parent_relations: Mapped[list["ConceptRelation"]] = relationship(
        foreign_keys="ConceptRelation.parent_concept_id",
        back_populates="parent_concept",
        cascade="all, delete-orphan",
    )
    child_relations: Mapped[list["ConceptRelation"]] = relationship(
        foreign_keys="ConceptRelation.child_concept_id",
        back_populates="child_concept",
        cascade="all, delete-orphan",
    )
    pages: Mapped[list["ConceptPage"]] = relationship(
        back_populates="concept",
        cascade="all, delete-orphan",
        order_by="ConceptPage.version.desc()",
    )
    state: Mapped["UserConceptState | None"] = relationship(
        back_populates="concept",
        uselist=False,
        cascade="all, delete-orphan",
    )

    @property
    def aliases(self) -> list[str]:
        if not self.aliases_json:
            return []
        try:
            value = json.loads(self.aliases_json)
        except json.JSONDecodeError:
            return []
        return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


class ConceptRelation(Base):
    __tablename__ = "concept_relations"
    __table_args__ = (
        UniqueConstraint("parent_concept_id", "child_concept_id", "relation_type", name="uq_concept_relation"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    parent_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    child_concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False, default="prerequisite")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent_concept: Mapped["Concept"] = relationship(
        foreign_keys=[parent_concept_id],
        back_populates="parent_relations",
    )
    child_concept: Mapped["Concept"] = relationship(
        foreign_keys=[child_concept_id],
        back_populates="child_relations",
    )


class UserConceptState(Base):
    __tablename__ = "user_concept_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_id: Mapped[int] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    concept: Mapped["Concept"] = relationship(back_populates="state")


class ConceptPage(Base):
    __tablename__ = "concept_pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    concept_id: Mapped[int] = mapped_column(ForeignKey("concepts.id", ondelete="CASCADE"), index=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    markdown_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    concept: Mapped["Concept"] = relationship(back_populates="pages")

    @property
    def content(self) -> dict | None:
        if not self.content_json:
            return None
        try:
            return json.loads(self.content_json)
        except json.JSONDecodeError:
            return None
