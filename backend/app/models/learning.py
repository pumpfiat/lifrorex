from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, Integer, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.content import ContentDifficulty, ContentStatus, ContentType, content_enum


class LearningProgression(str, Enum):
	INTRODUCE = "introduce"
	UNDERSTAND = "understand"
	RECOGNIZE = "recognize"
	APPLY = "apply"
	DECIDE = "decide"


learning_objective_knowledge = Table(
	"learning_objective_knowledge",
	Base.metadata,
	Column("objective_id", ForeignKey("learning_objectives.id", ondelete="CASCADE"), primary_key=True),
	Column("knowledge_id", ForeignKey("knowledge.id", ondelete="RESTRICT"), primary_key=True),
)

learning_objective_prerequisite = Table(
	"learning_objective_prerequisite",
	Base.metadata,
	Column("objective_id", ForeignKey("learning_objectives.id", ondelete="CASCADE"), primary_key=True),
	Column("prerequisite_id", ForeignKey("learning_objectives.id", ondelete="RESTRICT"), primary_key=True),
)


class LearningObjective(Base):
	"""A measurable learning aim grounded in existing Knowledge."""

	__tablename__ = "learning_objectives"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	title: Mapped[str] = mapped_column(String, nullable=False)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	difficulty: Mapped[ContentDifficulty] = mapped_column(
		content_enum(ContentDifficulty, "contentdifficulty"), nullable=False
	)
	progression: Mapped[LearningProgression] = mapped_column(
		SqlEnum(
			LearningProgression,
			name="learningprogression",
			values_callable=lambda enum: [member.value for member in enum],
		),
		nullable=False,
	)
	status: Mapped[ContentStatus] = mapped_column(
		content_enum(ContentStatus, "contentstatus"), default=ContentStatus.DRAFT, nullable=False
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	knowledge_records: Mapped[list["Knowledge"]] = relationship(secondary=learning_objective_knowledge)
	prerequisites: Mapped[list["LearningObjective"]] = relationship(
		secondary=learning_objective_prerequisite,
		primaryjoin=id == learning_objective_prerequisite.c.objective_id,
		secondaryjoin=id == learning_objective_prerequisite.c.prerequisite_id,
	)
	plans: Mapped[list["ContentPlan"]] = relationship(back_populates="objective")


class ContentPlan(Base):
	"""An ordered plan for the future Content needed to teach an objective."""

	__tablename__ = "content_plans"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	objective_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("learning_objectives.id", ondelete="CASCADE"), nullable=False
	)
	content_type: Mapped[ContentType] = mapped_column(
		content_enum(ContentType, "contenttype"), nullable=False
	)
	sequence: Mapped[int] = mapped_column(Integer, nullable=False)
	difficulty: Mapped[ContentDifficulty] = mapped_column(
		content_enum(ContentDifficulty, "contentdifficulty"), nullable=False
	)
	progression: Mapped[LearningProgression] = mapped_column(
		SqlEnum(
			LearningProgression,
			name="learningprogression",
			values_callable=lambda enum: [member.value for member in enum],
		),
		nullable=False,
	)
	objective: Mapped[LearningObjective] = relationship(back_populates="plans")

	__table_args__ = (UniqueConstraint("objective_id", "sequence", name="uq_content_plans_objective_sequence"),)