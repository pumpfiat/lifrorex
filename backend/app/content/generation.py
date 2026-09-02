"""Optional, knowledge-grounded content generators."""

import json
from typing import Any, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.api.schemas.content import ContentCreate
from app.api.schemas.content_creation import ContentCreationSpec
from app.api.schemas.knowledge import NonEmptyString
from app.config import settings
from app.models.content import ContentCreationMethod, ContentStatus, ContentType


class KnowledgeMaterial(BaseModel):
	"""Explicit Knowledge and evidence authorized for one generation attempt."""

	model_config = ConfigDict(extra="forbid", frozen=True)

	knowledge_id: int
	content: NonEmptyString
	evidence: tuple[NonEmptyString, ...]


class SupportingEvidence(BaseModel):
	model_config = ConfigDict(extra="forbid")

	knowledge_id: int
	evidence_text: NonEmptyString


class GeneratedContent(BaseModel):
	model_config = ConfigDict(extra="forbid")

	title: NonEmptyString
	body: NonEmptyString
	payload: dict[str, Any]
	supporting_evidence: list[SupportingEvidence]


class ContentGenerationError(Exception):
	"""Raised when a generator cannot produce a validated grounded draft."""


class ContentGenerator(Protocol):
	"""Returns a validated draft without persistence or provider coupling."""

	def generate(
		self, spec: ContentCreationSpec, material: list[KnowledgeMaterial]
	) -> ContentCreate:
		"""Generate one ContentCreate contract from explicitly supplied material."""


_SUPPORTING_EVIDENCE_SCHEMA = {
	"type": "array",
	"items": {
		"type": "object",
		"properties": {"knowledge_id": {"type": "integer"}, "evidence_text": {"type": "string"}},
		"required": ["knowledge_id", "evidence_text"],
		"additionalProperties": False,
	},
}

_PAYLOAD_SCHEMAS = {
	ContentType.CONCEPT: {
		"type": "object",
		"properties": {"name": {"type": "string"}, "summary": {"type": "string"}, "key_points": {"type": "array", "items": {"type": "string"}}},
		"required": ["name", "summary"],
		"additionalProperties": False,
	},
	ContentType.GLOSSARY: {
		"type": "object",
		"properties": {"term": {"type": "string"}, "definition": {"type": "string"}, "simple_explanation": {"type": "string"}, "example": {"type": "string"}},
		"required": ["term", "definition"],
		"additionalProperties": False,
	},
	ContentType.LESSON: {
		"type": "object",
		"properties": {
			"introduction": {"type": "string"},
			"sections": {"type": "array", "items": {"type": "object", "properties": {"heading": {"type": "string"}, "body": {"type": "string"}}, "required": ["heading", "body"], "additionalProperties": False}},
			"key_takeaways": {"type": "array", "items": {"type": "string"}},
		},
		"required": ["introduction", "sections", "key_takeaways"],
		"additionalProperties": False,
	},
	ContentType.QUESTION: {
		"type": "object",
		"properties": {"prompt": {"type": "string"}, "answer": {"type": "string"}, "explanation": {"type": "string"}, "options": {"type": "array", "items": {"type": "string"}}, "correct_option": {"type": "integer"}},
		"required": ["prompt", "answer", "explanation"],
		"additionalProperties": False,
	},
}


def response_schema(content_type: ContentType) -> dict[str, Any]:
	"""Return the provider JSON schema for one existing typed Content payload."""
	return {
		"type": "object",
		"properties": {
			"title": {"type": "string"},
			"body": {"type": "string"},
			"payload": _PAYLOAD_SCHEMAS[content_type],
			"supporting_evidence": _SUPPORTING_EVIDENCE_SCHEMA,
		},
		"required": ["title", "body", "payload", "supporting_evidence"],
		"additionalProperties": False,
	}

SYSTEM_INSTRUCTION = (
	"You write one learner-facing Liforex content draft of the specified type. Use only the supplied "
	"Knowledge material and evidence. Do not add facts or invent citations. Return "
	"only the requested JSON. Fill every required payload field with non-empty text and cite one "
	"or more supplied evidence excerpts exactly."
)


class OllamaContentGenerator:
	"""Optional Ollama writer for one grounded draft of a specified Content type."""

	def __init__(
		self,
		base_url: str = settings.ollama_base_url,
		model: str = settings.ollama_model,
		timeout_seconds: float = 30.0,
		transport: httpx.BaseTransport | None = None,
	) -> None:
		if not base_url.strip() or not model.strip() or timeout_seconds <= 0:
			raise ValueError("base_url, model, and timeout_seconds must be valid")
		self.base_url = base_url.rstrip("/")
		self.model = model
		self.timeout_seconds = timeout_seconds
		self.transport = transport

	def generate(
		self, spec: ContentCreationSpec, material: list[KnowledgeMaterial]
	) -> ContentCreate:
		self._validate_material(spec, material)
		try:
			with httpx.Client(base_url=self.base_url, timeout=self.timeout_seconds, transport=self.transport) as client:
				response = client.post("/api/chat", json=self._request_body(spec, material))
				response.raise_for_status()
				generated = GeneratedContent.model_validate(json.loads(response.json()["message"]["content"]))
				self._validate_grounding(generated.supporting_evidence, material)
				return ContentCreate(
					content_type=spec.content_type,
					status=ContentStatus.DRAFT,
					difficulty=spec.difficulty,
					title=generated.title,
					body=generated.body,
					payload=generated.payload,
					creation_method=ContentCreationMethod.LLM_GENERATED,
					knowledge_ids=list(spec.knowledge_ids),
				)
		except ContentGenerationError:
			raise
		except (httpx.HTTPError, KeyError, TypeError, ValueError, ValidationError) as error:
			raise ContentGenerationError("Ollama content generation failed") from error

	def _request_body(self, spec: ContentCreationSpec, material: list[KnowledgeMaterial]) -> dict[str, Any]:
		return {
			"model": self.model,
			"stream": False,
			"format": response_schema(spec.content_type),
			"messages": [
				{"role": "system", "content": SYSTEM_INSTRUCTION},
				{"role": "user", "content": json.dumps({"specification": spec.model_dump(mode="json"), "material": [item.model_dump() for item in material]})},
			],
		}

	@staticmethod
	def _validate_material(spec: ContentCreationSpec, material: list[KnowledgeMaterial]) -> None:
		if not material:
			raise ContentGenerationError("knowledge material is required")
		material_ids = [item.knowledge_id for item in material]
		if len(material_ids) != len(set(material_ids)) or set(material_ids) != set(spec.knowledge_ids):
			raise ContentGenerationError("material must match the specification Knowledge IDs")
		if any(not item.evidence for item in material):
			raise ContentGenerationError("knowledge material must include evidence")

	@staticmethod
	def _validate_grounding(supporting: list[SupportingEvidence], material: list[KnowledgeMaterial]) -> None:
		if not supporting:
			raise ContentGenerationError("generated content must include supporting evidence")
		evidence_by_knowledge = {item.knowledge_id: set(item.evidence) for item in material}
		for reference in supporting:
			if reference.evidence_text not in evidence_by_knowledge.get(reference.knowledge_id, set()):
				raise ContentGenerationError("generated content cited unsupported evidence")


__all__ = [
	"ContentGenerationError",
	"ContentGenerator",
	"KnowledgeMaterial",
	"OllamaContentGenerator",
]