from __future__ import annotations

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class LearnerProgressStatus(str, Enum):
	NOT_STARTED = "not_started"
	IN_PROGRESS = "in_progress"
	COMPLETED = "completed"


class LearnerObjectiveProgress(Base):
	"""User-specific progress for one global Learning Objective."""

	__tablename__ = "learner_objective_progress"

	id: Mapped[int] = mapped_column(Integer, primary_key=True)
	learner_id: Mapped[int] = mapped_column(Integer, nullable=False)
	objective_id: Mapped[int] = mapped_column(
		Integer, ForeignKey("learning_objectives.id", ondelete="RESTRICT"), nullable=False
	)
	status: Mapped[LearnerProgressStatus] = mapped_column(
		SqlEnum(
			LearnerProgressStatus,
			name="learnerprogressstatus",
			values_callable=lambda enum: [member.value for member in enum],
		),
		default=LearnerProgressStatus.NOT_STARTED,
		nullable=False,
	)
	started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), nullable=False
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
	)

	objective: Mapped["LearningObjective"] = relationship()

	__table_args__ = (
		UniqueConstraint("learner_id", "objective_id", name="uq_learner_objective_progress"),
	)