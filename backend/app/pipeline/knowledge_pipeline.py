"""One-document orchestration for the Knowledge Engine."""

import logging
from dataclasses import dataclass
from enum import Enum

from sqlalchemy.orm import Session

from app.api.schemas.knowledge import EvidenceCreate, KnowledgeCreate
from app.knowledge.extraction import KnowledgeExtractor
from app.services.document_repository import DocumentRepository
from app.services.evidence_repository import EvidenceRepository
from app.services.knowledge_repository import KnowledgeRepository


logger = logging.getLogger(__name__)


class KnowledgeProcessingStatus(str, Enum):
	COMPLETED = "completed"
	EMPTY_DOCUMENT = "empty_document"


class KnowledgeProcessingError(Exception):
	"""Raised when one-document knowledge processing cannot complete."""


@dataclass(frozen=True)
class KnowledgeProcessingResult:
	status: KnowledgeProcessingStatus
	document_id: int
	extracted_count: int = 0
	created_count: int = 0
	duplicate_count: int = 0
	evidence_count: int = 0
	knowledge_ids: tuple[int, ...] = ()


class KnowledgeProcessingPipeline:
	"""Coordinates extraction, canonical knowledge persistence, and evidence."""

	def __init__(self, extractor: KnowledgeExtractor, database_session: Session):
		self.extractor = extractor
		self.session = database_session
		self.documents = DocumentRepository(database_session)
		self.knowledge = KnowledgeRepository(database_session)
		self.evidence = EvidenceRepository(database_session)

	def process_document(self, document_id: int) -> KnowledgeProcessingResult:
		"""Process one persisted document atomically without provider coupling."""
		document = self.documents.get_by_id(document_id)
		if document is None:
			raise KnowledgeProcessingError(f"Document {document_id} was not found")
		if not document.content.strip():
			return KnowledgeProcessingResult(
				status=KnowledgeProcessingStatus.EMPTY_DOCUMENT, document_id=document_id
			)

		logger.info("knowledge_pipeline_started document_id=%s", document_id)
		try:
			candidates = self.extractor.extract(document)
			created_count = 0
			duplicate_count = 0
			evidence_count = 0
			knowledge_ids: list[int] = []
			for candidate in candidates:
				validated = KnowledgeCreate.model_validate(candidate)
				if validated.document_id != document.id:
					raise KnowledgeProcessingError("Extractor returned a candidate for another document")
				canonical, created = self.knowledge.create_or_get(validated, commit=False)
				knowledge_ids.append(canonical.id)
				created_count += int(created)
				duplicate_count += int(not created)
				if validated.evidence is not None:
					evidence, evidence_created = self.evidence.create_or_get(
						EvidenceCreate(
							knowledge_id=canonical.id,
							document_id=document.id,
							**validated.evidence.model_dump(),
						),
						commit=False,
					)
					evidence_count += int(evidence_created)
			self.session.commit()
		except Exception as error:
			self.session.rollback()
			if isinstance(error, KnowledgeProcessingError):
				raise
			raise KnowledgeProcessingError("Knowledge processing failed") from error

		logger.info(
			"knowledge_pipeline_completed document_id=%s extracted=%s created=%s duplicates=%s evidence=%s",
			document_id,
			len(candidates),
			created_count,
			duplicate_count,
			evidence_count,
		)
		return KnowledgeProcessingResult(
			status=KnowledgeProcessingStatus.COMPLETED,
			document_id=document_id,
			extracted_count=len(candidates),
			created_count=created_count,
			duplicate_count=duplicate_count,
			evidence_count=evidence_count,
			knowledge_ids=tuple(knowledge_ids),
		)


__all__ = [
	"KnowledgeProcessingError",
	"KnowledgeProcessingPipeline",
	"KnowledgeProcessingResult",
	"KnowledgeProcessingStatus",
]