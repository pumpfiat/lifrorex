from pydantic import BaseModel, ConfigDict, PositiveInt

from app.api.schemas.knowledge import NonEmptyString
from app.models.content import ContentDifficulty, ContentType
from app.models.learning import LearningProgression


class ContentCreationSpec(BaseModel):
	"""Deterministic requirements for creating one future Content item."""

	model_config = ConfigDict(frozen=True)

	content_plan_id: PositiveInt
	objective_id: PositiveInt
	content_type: ContentType
	difficulty: ContentDifficulty
	progression: LearningProgression
	sequence: int
	title_guidance: NonEmptyString
	objective_description: NonEmptyString
	knowledge_ids: tuple[PositiveInt, ...]
	required_fields: tuple[str, ...]