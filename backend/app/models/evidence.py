from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Evidence(Base):
	"""A document passage supporting a persisted Knowledge record."""

	__tablename__ = "evidence"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	knowledge_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("knowledge.id", ondelete="RESTRICT"), nullable=False
	)
	document_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
	)
	text: Mapped[str] = mapped_column(Text, nullable=False)
	start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
	end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)

	knowledge: Mapped["Knowledge"] = relationship()
	document: Mapped["Document"] = relationship()

	__table_args__ = (
		Index("ix_evidence_knowledge_id", "knowledge_id"),
		Index("ix_evidence_document_id", "document_id"),
	)