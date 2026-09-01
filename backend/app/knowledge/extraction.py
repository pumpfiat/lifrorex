"""Provider-independent contracts for extracting knowledge from documents."""

from typing import Protocol, TypeAlias

from app.api.schemas.knowledge import KnowledgeCreate
from app.models.document import Document


KnowledgeCandidates: TypeAlias = list[KnowledgeCreate]
"""Validated knowledge candidates produced from one document."""


class KnowledgeExtractionError(Exception):
	"""Raised when knowledge extraction cannot produce candidates."""


class KnowledgeExtractor(Protocol):
	"""Produces validated Knowledge candidates from one persisted Document.

	Implementations preserve ``document.id`` in each candidate's ``document_id``.
	They do not persist candidates or modify the document.
	"""

	def extract(self, document: Document) -> KnowledgeCandidates:
		"""Extract zero or more validated knowledge candidates from a document."""


__all__ = [
	"KnowledgeCandidates",
	"KnowledgeExtractionError",
	"KnowledgeExtractor",
]