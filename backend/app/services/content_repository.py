from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.content import ContentCreate, ContentUpdate
from app.models.content import (
	Content,
	ContentCreationMethod,
	ContentDifficulty,
	ContentStatus,
	ContentType,
)
from app.models.knowledge import Knowledge


class ContentRepository:
	"""Repository for content that references, but never duplicates, Knowledge."""

	def __init__(self, session: Session):
		self.session = session

	def create(self, content: ContentCreate) -> Content:
		"""Persist content with its authoritative Knowledge references."""
		knowledge_records = self._knowledge_records(content.knowledge_ids)
		try:
			db_content = Content(
				**content.model_dump(
					exclude={"knowledge_ids"}, mode="json", exclude_none=True
				),
				knowledge_records=knowledge_records,
			)
			self.session.add(db_content)
			self.session.commit()
			self.session.refresh(db_content)
			return db_content
		except Exception:
			self.session.rollback()
			raise

	def get_by_id(self, content_id: int) -> Content | None:
		"""Retrieve content by its stable identity."""
		stmt = (
			select(Content)
			.options(selectinload(Content.knowledge_records))
			.where(Content.id == content_id)
		)
		return self.session.scalars(stmt).first()

	def list(
		self,
		content_type: ContentType | None = None,
		status: ContentStatus | None = None,
		difficulty: ContentDifficulty | None = None,
		creation_method: ContentCreationMethod | None = None,
		knowledge_id: int | None = None,
		limit: int = 100,
		offset: int = 0,
	) -> list[Content]:
		"""List Content in deterministic pages with optional exact filters."""
		if limit <= 0:
			raise ValueError("limit must be positive")
		if offset < 0:
			raise ValueError("offset must be non-negative")
		stmt = select(Content).options(selectinload(Content.knowledge_records))
		if content_type is not None:
			stmt = stmt.where(Content.content_type == content_type)
		if status is not None:
			stmt = stmt.where(Content.status == status)
		if difficulty is not None:
			stmt = stmt.where(Content.difficulty == difficulty)
		if creation_method is not None:
			stmt = stmt.where(Content.creation_method == creation_method)
		if knowledge_id is not None:
			stmt = stmt.join(Content.knowledge_records).where(Knowledge.id == knowledge_id)
		stmt = stmt.order_by(Content.id).limit(limit).offset(offset)
		return list(self.session.scalars(stmt).all())

	def update(self, content_id: int, update: ContentUpdate) -> Content | None:
		"""Apply validated mutable fields and replace Knowledge references atomically."""
		existing = self.get_by_id(content_id)
		if existing is None:
			return None
		changes = update.model_dump(exclude_unset=True, mode="json")
		knowledge_ids = changes.pop(
			"knowledge_ids", [knowledge.id for knowledge in existing.knowledge_records]
		)
		validated = ContentCreate.model_validate(
			{
				"content_type": existing.content_type,
				"status": existing.status,
				"difficulty": existing.difficulty,
				"title": existing.title,
				"body": existing.body,
				"payload": existing.payload,
				"creation_method": existing.creation_method,
				"knowledge_ids": knowledge_ids,
				**changes,
			}
		)
		knowledge_records = self._knowledge_records(validated.knowledge_ids)
		try:
			for field_name, value in validated.model_dump(
				exclude={"content_type", "knowledge_ids"}, mode="json", exclude_none=True
			).items():
				setattr(existing, field_name, value)
			existing.knowledge_records = knowledge_records
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except Exception:
			self.session.rollback()
			raise

	def publish(self, content_id: int) -> Content | None:
		"""Explicitly mark Content as published."""
		return self._set_status(content_id, ContentStatus.PUBLISHED)

	def archive(self, content_id: int) -> Content | None:
		"""Archive Content without deleting its provenance or identity."""
		return self._set_status(content_id, ContentStatus.ARCHIVED)

	def _set_status(self, content_id: int, status: ContentStatus) -> Content | None:
		existing = self.get_by_id(content_id)
		if existing is None:
			return None
		try:
			existing.status = status
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except Exception:
			self.session.rollback()
			raise

	def _knowledge_records(self, knowledge_ids: list[int]) -> list[Knowledge]:
		knowledge_records = list(
			self.session.scalars(
				select(Knowledge).where(Knowledge.id.in_(knowledge_ids))
			).all()
		)
		if len(knowledge_records) != len(knowledge_ids):
			raise ValueError("knowledge_ids must reference existing Knowledge records")
		return knowledge_records


__all__ = ["ContentRepository"]