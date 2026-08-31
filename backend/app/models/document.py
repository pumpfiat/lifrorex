from datetime import datetime

from sqlalchemy import (
	JSON,
	DateTime,
	ForeignKey,
	Index,
	Integer,
	String,
	Text,
	UniqueConstraint,
	func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Document(Base):
	"""SQLAlchemy ORM model for persisted documents."""

	__tablename__ = "documents"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	source_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False
	)
	source_url: Mapped[str] = mapped_column(String, nullable=False)
	canonical_url: Mapped[str | None] = mapped_column(String, nullable=True)
	title: Mapped[str | None] = mapped_column(String, nullable=True)
	description: Mapped[str | None] = mapped_column(Text, nullable=True)
	author: Mapped[str | None] = mapped_column(String, nullable=True)
	published_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), nullable=True
	)
	modified_at: Mapped[datetime | None] = mapped_column(
		DateTime(timezone=True), nullable=True
	)
	content: Mapped[str] = mapped_column(Text, default="", nullable=False)
	content_type: Mapped[str | None] = mapped_column(String, nullable=True)
	http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
	extraction_status: Mapped[str] = mapped_column(
		String, default="pending", nullable=False
	)
	meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
	fingerprint: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
	fingerprint_version: Mapped[str | None] = mapped_column(String, nullable=True)
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
		Index("ix_documents_source_id", "source_id"),
		Index("ix_documents_fingerprint", "fingerprint"),
		# Was imported but never applied -- nothing previously stopped the same
		# URL from being ingested twice as separate rows. The fingerprint
		# unique constraint doesn't cover this: it only catches duplicates
		# once content has been fetched and fingerprinted, not a re-crawl of
		# the same URL before that point.
		UniqueConstraint("source_id", "source_url", name="uq_documents_source_id_source_url"),
	)
