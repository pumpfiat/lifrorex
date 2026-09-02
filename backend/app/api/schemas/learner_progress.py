from datetime import datetime

from pydantic import BaseModel, ConfigDict, PositiveInt

from app.models.learner_progress import LearnerProgressStatus


class LearnerObjectiveProgressCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	learner_id: PositiveInt
	objective_id: PositiveInt
	status: LearnerProgressStatus = LearnerProgressStatus.NOT_STARTED


class LearnerObjectiveProgressResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	learner_id: int
	objective_id: int
	status: LearnerProgressStatus
	started_at: datetime | None
	completed_at: datetime | None
	created_at: datetime
	updated_at: datetime


class SequenceProgress(BaseModel):
	model_config = ConfigDict(frozen=True)

	sequence_id: int
	learner_id: int
	completed_count: int
	total_count: int
	percentage: float
	next_objective_id: int | None