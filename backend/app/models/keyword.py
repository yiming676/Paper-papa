import json
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class KeywordNode(Base):
    __tablename__ = "keyword_nodes"
    __table_args__ = (
        UniqueConstraint("stable_key", name="uq_keyword_nodes_stable_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_keyword: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    keyword_type: Mapped[str] = mapped_column(String(50), nullable=False, default="term")
    source_sentence: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_keyword_id: Mapped[int | None] = mapped_column(ForeignKey("keyword_nodes.id", ondelete="CASCADE"), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    stable_key: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    explanation_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotated_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_status: Mapped[str] = mapped_column(String(50), nullable=False, default="stub")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    aliases_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="keyword_nodes")
    parent: Mapped["KeywordNode | None"] = relationship(
        remote_side=[id],
        back_populates="children",
    )
    children: Mapped[list["KeywordNode"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
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

    @property
    def explanation(self) -> dict | None:
        if not self.explanation_content:
            return None
        try:
            value = json.loads(self.explanation_content)
        except json.JSONDecodeError:
            return None
        return value if isinstance(value, dict) else None
