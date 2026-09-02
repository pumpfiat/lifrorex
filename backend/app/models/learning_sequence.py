from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.content import ContentDifficulty, ContentStatus, content_enum


class LearningSequence(Base):
	"""An ordered path through reusable Learning Objectives."""

	__tablename__ = "learning_sequences"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	title: Mapped[str] = mapped_column(String, nullable=False)
	description: Mapped[str] = mapped_column(Text, nullable=False)
	status: Mapped[ContentStatus] = mapped_column(
		content_enum(ContentStatus, "contentstatus"), default=ContentStatus.DRAFT, nullable=False
	)
	difficulty: Mapped[ContentDifficulty] = mapped_column(
		content_enum(ContentDifficulty, "contentdifficulty"), nullable=False
	)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	items: Mapped[list["LearningSequenceItem"]] = relationship(
		back_populates="sequence", cascade="all, delete-orphan", order_by="LearningSequenceItem.position"
	)


class LearningSequenceItem(Base):
	"""One Learning Objective positioned within a Learning Sequence."""

	__tablename__ = "learning_sequence_items"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	sequence_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("learning_sequences.id", ondelete="CASCADE"), nullable=False
	)
	objective_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("learning_objectives.id", ondelete="RESTRICT"), nullable=False
	)
	position: Mapped[int] = mapped_column(Integer, nullable=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)

	sequence: Mapped[LearningSequence] = relationship(back_populates="items")
	objective: Mapped["LearningObjective"] = relationship()

	__table_args__ = (
		UniqueConstraint("sequence_id", "objective_id", name="uq_learning_sequence_objective"),
		UniqueConstraint("sequence_id", "position", name="uq_learning_sequence_position"),
	)