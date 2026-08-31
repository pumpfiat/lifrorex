from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.schemas.knowledge import KnowledgeCreate, KnowledgeUpdate
from app.models.knowledge import Knowledge


class KnowledgeRepository:
	"""Repository for persisting and retrieving Knowledge objects."""

	def __init__(self, session: Session):
		self.session = session

	def get_by_id(self, knowledge_id: int) -> Knowledge | None:
		"""Retrieve a Knowledge record by ID."""
		stmt = select(Knowledge).where(Knowledge.id == knowledge_id)
		return self.session.scalars(stmt).first()

	def get_by_document_id(
		self, document_id: int, limit: int = 100, offset: int = 0
	) -> list[Knowledge]:
		"""Retrieve Knowledge records for a document in deterministic pages."""
		if limit <= 0:
			raise ValueError("limit must be positive")
		if offset < 0:
			raise ValueError("offset must be non-negative")
		stmt = (
			select(Knowledge)
			.where(Knowledge.document_id == document_id)
			.order_by(Knowledge.id)
			.limit(limit)
			.offset(offset)
		)
		return list(self.session.scalars(stmt).all())

	def create(self, knowledge: KnowledgeCreate) -> Knowledge:
		"""Create and persist one validated Knowledge record."""
		db_knowledge = Knowledge(**knowledge.model_dump())
		try:
			self.session.add(db_knowledge)
			self.session.commit()
			self.session.refresh(db_knowledge)
			return db_knowledge
		except IntegrityError:
			self.session.rollback()
			raise

	def create_many(self, knowledge_records: list[KnowledgeCreate]) -> list[Knowledge]:
		"""Create validated Knowledge records atomically with one commit."""
		if not knowledge_records:
			return []

		db_knowledge_records = [
			Knowledge(**knowledge.model_dump()) for knowledge in knowledge_records
		]
		try:
			self.session.add_all(db_knowledge_records)
			self.session.commit()
			for db_knowledge in db_knowledge_records:
				self.session.refresh(db_knowledge)
			return db_knowledge_records
		except IntegrityError:
			self.session.rollback()
			raise

	def update(
		self, knowledge_id: int, knowledge: KnowledgeUpdate
	) -> Knowledge | None:
		"""Apply supplied fields to a Knowledge record and persist it."""
		existing = self.get_by_id(knowledge_id)
		if existing is None:
			return None

		for field_name, value in knowledge.model_dump(exclude_unset=True).items():
			setattr(existing, field_name, value)

		try:
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except IntegrityError:
			self.session.rollback()
			raise

	def delete(self, knowledge_id: int) -> bool:
		"""Delete a Knowledge record, returning whether it existed."""
		knowledge = self.get_by_id(knowledge_id)
		if knowledge is None:
			return False

		self.session.delete(knowledge)
		self.session.commit()
		return True


__all__ = ["KnowledgeRepository"]