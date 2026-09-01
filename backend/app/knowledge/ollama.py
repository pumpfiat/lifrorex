"""Ollama adapter for the provider-neutral knowledge extraction contract."""

import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.api.schemas.knowledge import EvidenceProposal, KnowledgeCreate
from app.config import settings
from app.knowledge.extraction import (
	KnowledgeCandidates,
	KnowledgeExtractionError,
)
from app.models.document import Document


EXTRACTION_RESPONSE_SCHEMA = {
	"type": "object",
	"properties": {
		"candidates": {
			"type": "array",
			"items": {
				"type": "object",
				"properties": {
					"knowledge_type": {"type": "string"},
					"content": {"type": "string"},
					"meta": {"type": "object"},
					"evidence": {
						"type": "object",
						"properties": {"text": {"type": "string"}},
						"required": ["text"],
						"additionalProperties": False,
					},
				},
				"required": ["knowledge_type", "content"],
				"additionalProperties": False,
			},
		},
	},
	"required": ["candidates"],
	"additionalProperties": False,
}

SYSTEM_INSTRUCTION = (
	"You are a knowledge extraction component for Liforex. Extract useful "
	"educational knowledge supported by the supplied document. When the document "
	"contains a useful supported statement, return it as a candidate with an exact "
	"supporting passage copied verbatim from the document. Omit any candidate for "
	"which you cannot provide an exact supporting passage. Do not invent information. "
	"Return only JSON matching the requested schema."
)


class OllamaKnowledgeExtractor:
	"""Extract validated candidates through Ollama without persisting them."""

	def __init__(
		self,
		base_url: str = settings.ollama_base_url,
		model: str = settings.ollama_model,
		timeout_seconds: float = 30.0,
		transport: httpx.BaseTransport | None = None,
	) -> None:
		if not base_url.strip():
			raise ValueError("base_url must not be empty")
		if not model.strip():
			raise ValueError("model must not be empty")
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		self.base_url = base_url.rstrip("/")
		self.model = model
		self.timeout_seconds = timeout_seconds
		self.transport = transport

	def extract(self, document: Document) -> KnowledgeCandidates:
		"""Return validated candidates for one document or raise extraction error."""
		try:
			with httpx.Client(
				base_url=self.base_url,
				timeout=self.timeout_seconds,
				transport=self.transport,
			) as client:
				response = client.post(
					"/api/chat",
					json={
						"model": self.model,
						"stream": False,
						"format": EXTRACTION_RESPONSE_SCHEMA,
						"messages": [
							{"role": "system", "content": SYSTEM_INSTRUCTION},
							{"role": "user", "content": document.content},
						],
					},
				)
				response.raise_for_status()
				payload = response.json()
				content = payload["message"]["content"]
				candidates = json.loads(content)["candidates"]
				if not isinstance(candidates, list):
					raise ValueError("candidates must be a list")
				return [
					self._candidate_from_response(candidate, document)
					for candidate in candidates
				]
		except (
			httpx.HTTPError,
			json.JSONDecodeError,
			KeyError,
			TypeError,
			ValidationError,
			ValueError,
		) as error:
			raise KnowledgeExtractionError("Ollama knowledge extraction failed") from error

	@staticmethod
	def _candidate_from_response(candidate: object, document: Document) -> KnowledgeCreate:
		if not isinstance(candidate, dict):
			raise ValueError("candidate must be an object")
		candidate_data = dict(candidate)
		candidate_data.pop("document_id", None)
		candidate_data.pop("source_id", None)
		evidence = candidate_data.get("evidence")
		if evidence is not None:
			candidate_data["evidence"] = OllamaKnowledgeExtractor._validate_evidence(
				evidence, document.content
			)
		return KnowledgeCreate.model_validate({**candidate_data, "document_id": document.id})

	@staticmethod
	def _validate_evidence(evidence: object, document_content: str) -> EvidenceProposal:
		if not isinstance(evidence, dict):
			raise ValueError("evidence must be an object")
		evidence_data = dict(evidence)
		evidence_data.pop("document_id", None)
		evidence_data.pop("source_id", None)
		proposal = EvidenceProposal.model_validate(evidence_data)
		start_offset = document_content.find(proposal.text)
		if start_offset < 0:
			raise ValueError("evidence text must occur in document content")
		end_offset = start_offset + len(proposal.text)
		if proposal.start_offset is not None and (
			proposal.start_offset != start_offset or proposal.end_offset != end_offset
		):
			raise ValueError("evidence offsets must locate evidence text in document content")
		return EvidenceProposal(
			text=proposal.text,
			start_offset=start_offset,
			end_offset=end_offset,
		)


__all__ = ["OllamaKnowledgeExtractor"]