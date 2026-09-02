from app.api.schemas.learner_progress import SequenceProgress
from app.models.learning import LearningObjective
from app.models.learner_progress import LearnerObjectiveProgress, LearnerProgressStatus
from app.services.learner_progress_repository import LearnerProgressRepository
from app.services.learning_repository import LearningRepository
from app.services.learning_sequence_repository import LearningSequenceRepository


class LearnerProgressError(Exception):
	"""Raised when a learner cannot make the requested objective transition."""


class LearnerProgressService:
	"""Applies deterministic learner progression rules over global objectives."""

	def __init__(
		self,
		repository: LearnerProgressRepository,
		learning_repository: LearningRepository,
		sequence_repository: LearningSequenceRepository,
	):
		self.repository = repository
		self.learning = learning_repository
		self.sequences = sequence_repository

	def start_objective(self, learner_id: int, objective_id: int) -> LearnerObjectiveProgress:
		objective = self._objective(objective_id)
		self._validate_prerequisites(learner_id, objective)
		progress = self.repository.create_or_get(learner_id, objective_id)
		if progress.status is LearnerProgressStatus.COMPLETED:
			raise LearnerProgressError("completed objectives cannot be restarted")
		if progress.status is LearnerProgressStatus.NOT_STARTED:
			return self.repository.set_status(progress, LearnerProgressStatus.IN_PROGRESS)
		return progress

	def complete_objective(self, learner_id: int, objective_id: int) -> LearnerObjectiveProgress:
		objective = self._objective(objective_id)
		self._validate_prerequisites(learner_id, objective)
		progress = self.repository.create_or_get(learner_id, objective_id)
		if progress.status is LearnerProgressStatus.COMPLETED:
			return progress
		return self.repository.set_status(progress, LearnerProgressStatus.COMPLETED)

	def get_objective_progress(self, learner_id: int, objective_id: int) -> LearnerObjectiveProgress | None:
		return self.repository.get(learner_id, objective_id)

	def get_sequence_progress(self, learner_id: int, sequence_id: int) -> SequenceProgress:
		items = self.sequences.list_objectives(sequence_id)
		completed_count = sum(
			self.repository.get(learner_id, item.objective_id) is not None
			and self.repository.get(learner_id, item.objective_id).status is LearnerProgressStatus.COMPLETED
			for item in items
		)
		total_count = len(items)
		return SequenceProgress(
			sequence_id=sequence_id,
			learner_id=learner_id,
			completed_count=completed_count,
			total_count=total_count,
			percentage=0.0 if total_count == 0 else completed_count * 100 / total_count,
			next_objective_id=self.get_next_objective(learner_id, sequence_id),
		)

	def get_next_objective(self, learner_id: int, sequence_id: int) -> int | None:
		for item in self.sequences.list_objectives(sequence_id):
			progress = self.repository.get(learner_id, item.objective_id)
			if progress is not None and progress.status is LearnerProgressStatus.COMPLETED:
				continue
			try:
				self._validate_prerequisites(learner_id, item.objective)
			except LearnerProgressError:
				continue
			return item.objective_id
		return None

	def _objective(self, objective_id: int) -> LearningObjective:
		objective = self.learning.get_objective(objective_id)
		if objective is None:
			raise LearnerProgressError("objective was not found")
		return objective

	def _validate_prerequisites(self, learner_id: int, objective: LearningObjective) -> None:
		for prerequisite in objective.prerequisites:
			progress = self.repository.get(learner_id, prerequisite.id)
			if progress is None or progress.status is not LearnerProgressStatus.COMPLETED:
				raise LearnerProgressError("objective prerequisites are not completed")


__all__ = ["LearnerProgressError", "LearnerProgressService"]