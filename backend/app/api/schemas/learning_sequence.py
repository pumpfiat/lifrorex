from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

from app.api.schemas.knowledge import NonEmptyString
from app.models.content import ContentDifficulty, ContentStatus


class LearningSequenceCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: NonEmptyString
	description: NonEmptyString
	difficulty: ContentDifficulty
	status: ContentStatus = ContentStatus.DRAFT


class LearningSequenceUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: NonEmptyString | None = None
	description: NonEmptyString | None = None
	difficulty: ContentDifficulty | None = None
	status: ContentStatus | None = None


class LearningSequenceItemCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	objective_id: PositiveInt
	position: int = Field(ge=1)


class LearningSequenceResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	title: str
	description: str
	status: ContentStatus
	difficulty: ContentDifficulty
	created_at: datetime
	updated_at: datetime


class LearningSequenceItemResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	sequence_id: int
	objective_id: int
	position: int
	created_at: datetime