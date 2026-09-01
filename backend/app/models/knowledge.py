from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, event, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.knowledge.deduplication import knowledge_fingerprint


class Knowledge(Base):
	"""SQLAlchemy ORM model for structured knowledge derived from a document."""

	__tablename__ = "knowledge"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	document_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("documents.id", ondelete="RESTRICT"), nullable=False
	)
	knowledge_type: Mapped[str] = mapped_column(String, nullable=False)
	content: Mapped[str] = mapped_column(Text, nullable=False)
	fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
	meta: Mapped[dict] = mapped_column("metadata", JSON, default=dict, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	__table_args__ = (
		Index("ix_knowledge_document_id", "document_id"),
		Index("ix_knowledge_knowledge_type", "knowledge_type"),
	)


@event.listens_for(Knowledge, "before_insert")
def assign_knowledge_fingerprint(mapper, connection, target) -> None:
	"""Preserve duplicate protection for direct ORM construction."""
	if target.fingerprint is None and isinstance(target.content, str):
		target.fingerprint = knowledge_fingerprint(target.content)