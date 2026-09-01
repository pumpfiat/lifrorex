from datetime import datetime
from typing import Annotated, Any

from pydantic import (
	BaseModel,
	ConfigDict,
	Field,
	PositiveInt,
	StringConstraints,
	model_validator,
)


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class EvidenceProposal(BaseModel):
	"""Evidence proposed during extraction before a Knowledge record exists."""

	model_config = ConfigDict(extra="forbid")

	text: NonEmptyString
	start_offset: int | None = Field(default=None, ge=0)
	end_offset: int | None = Field(default=None, ge=0)

	@model_validator(mode="after")
	def validate_offsets(self) -> "EvidenceProposal":
		if (self.start_offset is None) != (self.end_offset is None):
			raise ValueError("start_offset and end_offset must be supplied together")
		if self.start_offset is not None and self.end_offset <= self.start_offset:
			raise ValueError("end_offset must be greater than start_offset")
		return self


class EvidenceCreate(EvidenceProposal):
	"""Validated evidence ready to be persisted for existing Knowledge."""

	knowledge_id: PositiveInt
	document_id: PositiveInt


class KnowledgeCreate(BaseModel):
	model_config = ConfigDict(extra="forbid")

	document_id: PositiveInt
	knowledge_type: NonEmptyString
	content: NonEmptyString
	meta: dict[str, Any] = Field(default_factory=dict)
	evidence: EvidenceProposal | None = None


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