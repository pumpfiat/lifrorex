from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator

from app.api.schemas.knowledge import NonEmptyString
from app.models.content import (
	ContentCreationMethod,
	ContentDifficulty,
	ContentStatus,
	ContentType,
)


class ConceptPayload(BaseModel):
	model_config = ConfigDict(extra="forbid")

	name: NonEmptyString
	summary: NonEmptyString
	key_points: list[NonEmptyString] = Field(default_factory=list)


class GlossaryPayload(BaseModel):
	model_config = ConfigDict(extra="forbid")

	term: NonEmptyString
	definition: NonEmptyString
	simple_explanation: NonEmptyString | None = None
	example: NonEmptyString | None = None


class LessonSection(BaseModel):
	model_config = ConfigDict(extra="forbid")

	heading: NonEmptyString
	body: NonEmptyString


class LessonPayload(BaseModel):
	model_config = ConfigDict(extra="forbid")

	introduction: NonEmptyString
	sections: list[LessonSection] = Field(min_length=1)
	key_takeaways: list[NonEmptyString] = Field(min_length=1)


class QuestionPayload(BaseModel):
	model_config = ConfigDict(extra="forbid")

	prompt: NonEmptyString
	answer: NonEmptyString
	explanation: NonEmptyString
	options: list[NonEmptyString] | None = None
	correct_option: int | None = Field(default=None, ge=0)

	@model_validator(mode="after")
	def validate_options(self) -> "QuestionPayload":
		if (self.options is None) != (self.correct_option is None):
			raise ValueError("options and correct_option must be supplied together")
		if self.options is not None:
			if len(self.options) < 2:
				raise ValueError("options must contain at least two choices")
			if len(set(self.options)) != len(self.options):
				raise ValueError("options must not contain duplicates")
			if self.correct_option >= len(self.options):
				raise ValueError("correct_option must reference an option")
		return self


ContentPayload = ConceptPayload | GlossaryPayload | LessonPayload | QuestionPayload


_PAYLOAD_SCHEMAS: dict[ContentType, type[ContentPayload]] = {
	ContentType.CONCEPT: ConceptPayload,
	ContentType.GLOSSARY: GlossaryPayload,
	ContentType.LESSON: LessonPayload,
	ContentType.QUESTION: QuestionPayload,
}


class ContentCreate(BaseModel):
	"""Validated learner-facing content grounded in existing Knowledge."""

	model_config = ConfigDict(extra="forbid")

	content_type: ContentType
	status: ContentStatus = ContentStatus.DRAFT
	difficulty: ContentDifficulty
	title: NonEmptyString
	body: NonEmptyString
	payload: ContentPayload
	creation_method: ContentCreationMethod
	knowledge_ids: list[PositiveInt] = Field(min_length=1)

	@model_validator(mode="before")
	@classmethod
	def validate_payload_type(cls, data: Any) -> Any:
		if not isinstance(data, dict):
			return data
		content_type = data.get("content_type")
		try:
			content_type = ContentType(content_type)
		except ValueError:
			return data
		payload_schema = _PAYLOAD_SCHEMAS[content_type]
		payload = data.get("payload")
		if isinstance(payload, payload_schema):
			return data
		return {**data, "payload": payload_schema.model_validate(payload)}

	@model_validator(mode="after")
	def validate_references_and_payload_type(self) -> "ContentCreate":
		if len(self.knowledge_ids) != len(set(self.knowledge_ids)):
			raise ValueError("knowledge_ids must not contain duplicates")
		if not isinstance(self.payload, _PAYLOAD_SCHEMAS[self.content_type]):
			raise ValueError("payload must match content_type")
		return self


class ContentUpdate(BaseModel):
	"""Mutable Content fields; content_type remains stable after creation."""

	model_config = ConfigDict(extra="forbid")

	difficulty: ContentDifficulty | None = None
	title: NonEmptyString | None = None
	body: NonEmptyString | None = None
	payload: dict[str, Any] | ContentPayload | None = None
	creation_method: ContentCreationMethod | None = None
	knowledge_ids: list[PositiveInt] | None = Field(default=None, min_length=1)

	@field_validator("knowledge_ids")
	@classmethod
	def validate_knowledge_ids(cls, value: list[int] | None) -> list[int] | None:
		if value is not None and len(value) != len(set(value)):
			raise ValueError("knowledge_ids must not contain duplicates")
		return value


class ContentResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	content_type: ContentType
	status: ContentStatus
	difficulty: ContentDifficulty
	title: str
	body: str
	payload: dict[str, Any]
	creation_method: ContentCreationMethod
	knowledge_ids: list[int]
	created_at: datetime
	updated_at: datetime