from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.schemas.knowledge import EvidenceCreate
from app.models.document import Document
from app.models.evidence import Evidence
from app.models.knowledge import Knowledge


class EvidenceRepository:
	"""Repository for evidence attached to already persisted Knowledge records."""

	def __init__(self, session: Session):
		self.session = session

	def create(self, evidence: EvidenceCreate, commit: bool = True) -> Evidence:
		"""Persist evidence after verifying its document matches the Knowledge record."""
		knowledge = self.session.get(Knowledge, evidence.knowledge_id)
		if knowledge is None:
			raise ValueError("knowledge_id does not reference an existing Knowledge record")
		document = self.session.get(Document, evidence.document_id)
		if document is None:
			raise ValueError("document_id does not reference an existing Document record")
		start_offset = document.content.find(evidence.text)
		if start_offset < 0:
			raise ValueError("evidence text must occur in document content")
		end_offset = start_offset + len(evidence.text)
		if evidence.start_offset is not None and (
			evidence.start_offset != start_offset or evidence.end_offset != end_offset
		):
			raise ValueError("evidence offsets must locate evidence text in document content")

		db_evidence = Evidence(**evidence.model_dump())
		self.session.add(db_evidence)
		if commit:
			self.session.commit()
		else:
			self.session.flush()
		self.session.refresh(db_evidence)
		return db_evidence

	def get_by_knowledge_id(self, knowledge_id: int) -> list[Evidence]:
		"""Retrieve evidence for one Knowledge record in deterministic order."""
		stmt = select(Evidence).where(Evidence.knowledge_id == knowledge_id).order_by(Evidence.id)
		return list(self.session.scalars(stmt).all())

	def create_or_get(self, evidence: EvidenceCreate, commit: bool = True) -> tuple[Evidence, bool]:
		"""Create evidence or return an identical existing provenance record."""
		stmt = select(Evidence).where(
			Evidence.knowledge_id == evidence.knowledge_id,
			Evidence.document_id == evidence.document_id,
			Evidence.text == evidence.text,
			Evidence.start_offset == evidence.start_offset,
			Evidence.end_offset == evidence.end_offset,
		)
		existing = self.session.scalars(stmt).first()
		if existing is not None:
			return existing, False
		return self.create(evidence, commit=commit), True


__all__ = ["EvidenceRepository"]