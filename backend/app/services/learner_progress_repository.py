from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.learner_progress import LearnerObjectiveProgress, LearnerProgressStatus


class LearnerProgressRepository:
	"""Persistence for learner-specific objective state."""

	def __init__(self, session: Session):
		self.session = session

	def get(self, learner_id: int, objective_id: int) -> LearnerObjectiveProgress | None:
		stmt = select(LearnerObjectiveProgress).where(
			LearnerObjectiveProgress.learner_id == learner_id,
			LearnerObjectiveProgress.objective_id == objective_id,
		)
		return self.session.scalars(stmt).first()

	def list(self, learner_id: int, status: LearnerProgressStatus | None = None) -> list[LearnerObjectiveProgress]:
		stmt = select(LearnerObjectiveProgress).where(LearnerObjectiveProgress.learner_id == learner_id)
		if status is not None:
			stmt = stmt.where(LearnerObjectiveProgress.status == status)
		return list(self.session.scalars(stmt.order_by(LearnerObjectiveProgress.objective_id)).all())

	def create_or_get(self, learner_id: int, objective_id: int) -> LearnerObjectiveProgress:
		existing = self.get(learner_id, objective_id)
		if existing is not None:
			return existing
		try:
			progress = LearnerObjectiveProgress(learner_id=learner_id, objective_id=objective_id)
			self.session.add(progress)
			self.session.commit()
			self.session.refresh(progress)
			return progress
		except IntegrityError:
			self.session.rollback()
			existing = self.get(learner_id, objective_id)
			if existing is not None:
				return existing
			raise

	def set_status(
		self, progress: LearnerObjectiveProgress, status: LearnerProgressStatus
	) -> LearnerObjectiveProgress:
		now = datetime.now(timezone.utc)
		try:
			progress.status = status
			if status is LearnerProgressStatus.IN_PROGRESS and progress.started_at is None:
				progress.started_at = now
			if status is LearnerProgressStatus.COMPLETED:
				if progress.started_at is None:
					progress.started_at = now
				progress.completed_at = now
			self.session.commit()
			self.session.refresh(progress)
			return progress
		except Exception:
			self.session.rollback()
			raise


__all__ = ["LearnerProgressRepository"]