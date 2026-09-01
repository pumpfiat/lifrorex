from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, JSON, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ContentType(str, Enum):
	CONCEPT = "concept"
	GLOSSARY = "glossary"
	LESSON = "lesson"
	QUESTION = "question"


class ContentStatus(str, Enum):
	DRAFT = "draft"
	REVIEW = "review"
	PUBLISHED = "published"
	ARCHIVED = "archived"


class ContentDifficulty(str, Enum):
	BEGINNER = "beginner"
	INTERMEDIATE = "intermediate"
	ADVANCED = "advanced"


class ContentCreationMethod(str, Enum):
	MANUAL = "manual"
	RULE_BASED = "rule_based"
	LLM_ASSISTED = "llm_assisted"
	LLM_GENERATED = "llm_generated"


content_knowledge = Table(
	"content_knowledge",
	Base.metadata,
	Column("content_id", ForeignKey("content.id", ondelete="CASCADE"), primary_key=True),
	Column("knowledge_id", ForeignKey("knowledge.id", ondelete="RESTRICT"), primary_key=True),
)


def content_enum(enum_class: type[Enum], name: str) -> SqlEnum:
	"""Store the controlled enum values used by the Content migration."""
	return SqlEnum(
		enum_class,
		name=name,
		values_callable=lambda enum: [member.value for member in enum],
	)


class Content(Base):
	"""A learner-facing representation grounded in existing Knowledge records."""

	__tablename__ = "content"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	content_type: Mapped[ContentType] = mapped_column(
		content_enum(ContentType, "contenttype"), nullable=False
	)
	status: Mapped[ContentStatus] = mapped_column(
		content_enum(ContentStatus, "contentstatus"), default=ContentStatus.DRAFT, nullable=False
	)
	difficulty: Mapped[ContentDifficulty] = mapped_column(
		content_enum(ContentDifficulty, "contentdifficulty"), nullable=False
	)
	title: Mapped[str] = mapped_column(String, nullable=False)
	body: Mapped[str] = mapped_column(Text, nullable=False)
	payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
	creation_method: Mapped[ContentCreationMethod] = mapped_column(
		content_enum(ContentCreationMethod, "contentcreationmethod"), nullable=False
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True),
		server_default=func.now(),
		onupdate=func.now(),
		nullable=False,
	)

	knowledge_records: Mapped[list["Knowledge"]] = relationship(secondary=content_knowledge)