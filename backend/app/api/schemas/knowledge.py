from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, StringConstraints


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class KnowledgeCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	document_id: PositiveInt
	knowledge_type: NonEmptyString
	content: NonEmptyString
	meta: dict[str, Any] = Field(default_factory=dict)


class KnowledgeUpdate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	document_id: PositiveInt | None = None
	knowledge_type: NonEmptyString | None = None
	content: NonEmptyString | None = None
	meta: dict[str, Any] | None = None


class KnowledgeResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	document_id: int
	knowledge_type: str
	content: str
	meta: dict[str, Any]
	created_at: datetime
	updated_at: datetime