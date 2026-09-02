from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

from app.api.schemas.knowledge import NonEmptyString
from app.models.content import ContentDifficulty, ContentStatus, ContentType
from app.models.learning import LearningProgression


class LearningObjectiveCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: NonEmptyString
	description: NonEmptyString
	difficulty: ContentDifficulty
	progression: LearningProgression
	status: ContentStatus = ContentStatus.DRAFT
	knowledge_ids: list[PositiveInt] = Field(min_length=1)
	prerequisite_ids: list[PositiveInt] = Field(default_factory=list)

	@field_validator("knowledge_ids", "prerequisite_ids")
	@classmethod
	def reject_duplicate_ids(cls, value: list[int]) -> list[int]:
		if len(value) != len(set(value)):
			raise ValueError("IDs must not contain duplicates")
		return value


class LearningObjectiveUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: NonEmptyString | None = None
	description: NonEmptyString | None = None
	difficulty: ContentDifficulty | None = None
	progression: LearningProgression | None = None
	status: ContentStatus | None = None
	knowledge_ids: list[PositiveInt] | None = Field(default=None, min_length=1)
	prerequisite_ids: list[PositiveInt] | None = None

	@field_validator("knowledge_ids", "prerequisite_ids")
	@classmethod
	def reject_duplicate_ids(cls, value: list[int] | None) -> list[int] | None:
		if value is not None and len(value) != len(set(value)):
			raise ValueError("IDs must not contain duplicates")
		return value


class ContentPlanCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	objective_id: PositiveInt
	content_type: ContentType
	sequence: int = Field(ge=1)
	difficulty: ContentDifficulty
	progression: LearningProgression


class ContentPlanUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	content_type: ContentType | None = None
	sequence: int | None = Field(default=None, ge=1)
	difficulty: ContentDifficulty | None = None
	progression: LearningProgression | None = None


class LearningObjectiveResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	title: str
	description: str
	difficulty: ContentDifficulty
	progression: LearningProgression
	status: ContentStatus
	knowledge_ids: list[int]
	prerequisite_ids: list[int]
	created_at: datetime
	updated_at: datetime


class ContentPlanResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	objective_id: int
	content_type: ContentType
	sequence: int
	difficulty: ContentDifficulty
	progression: LearningProgression