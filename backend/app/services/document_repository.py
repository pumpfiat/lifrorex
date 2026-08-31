from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.content.deduplication import fingerprint_document
from app.content.document import Document as PydanticDocument
from app.models.document import Document as DocumentModel


class DocumentRepository:
	"""Repository for persisting and retrieving Document objects."""

	def __init__(self, session: Session):
		self.session = session

	def create(
		self,
		document: PydanticDocument,
		source_id: int,
	) -> DocumentModel:
		"""
		Create and persist a new Document.

		Args:
			document: Pydantic Document contract
			source_id: ID of the source this document came from

		Returns:
			Persisted DocumentModel (ORM object)

		Raises:
			ValueError: If source does not exist or other validation errors
			IntegrityError: If unique constraints are violated
		"""
		# Compute fingerprint
		fingerprint = fingerprint_document(document)
		fingerprint_version = None
		if fingerprint != "empty":
			fingerprint_version = "v1"

		now = datetime.now(timezone.utc)

		# Create ORM model
		db_document = DocumentModel(
			source_id=source_id,
			source_url=document.source_url,
			canonical_url=document.canonical_url,
			title=document.title,
			description=document.description,
			author=document.author,
			published_at=document.published_at,
			modified_at=document.modified_at,
			content=document.content,
			content_type=document.content_type,
			http_status=document.http_status,
			extraction_status=document.extraction_status.value,
			meta=document.metadata,
			fingerprint=fingerprint if fingerprint != "empty" else None,
			fingerprint_version=fingerprint_version,
			created_at=now,
			updated_at=now,
		)

		try:
			self.session.add(db_document)
			self.session.commit()
			self.session.refresh(db_document)
			return db_document
		except IntegrityError as e:
			self.session.rollback()
			raise e

	def get_by_id(self, document_id: int) -> DocumentModel | None:
		"""Retrieve a document by ID."""
		stmt = select(DocumentModel).where(DocumentModel.id == document_id)
		return self.session.scalars(stmt).first()

	def get_by_fingerprint(self, fingerprint: str) -> DocumentModel | None:
		"""Retrieve a document by fingerprint."""
		if not fingerprint or fingerprint == "empty":
			return None
		stmt = select(DocumentModel).where(DocumentModel.fingerprint == fingerprint)
		return self.session.scalars(stmt).first()

	def get_all_by_source(self, source_id: int) -> list[DocumentModel]:
		"""Retrieve all documents from a given source."""
		stmt = select(DocumentModel).where(DocumentModel.source_id == source_id)
		return list(self.session.scalars(stmt).all())

	def update(
		self,
		document_id: int,
		document: PydanticDocument,
	) -> DocumentModel | None:
		"""
		Update an existing document.

		Preserves created_at but updates updated_at.
		If content changes, fingerprint is recomputed.

		Args:
			document_id: ID of document to update
			document: Updated Pydantic Document

		Returns:
			Updated DocumentModel or None if not found

		Raises:
			IntegrityError: If unique constraints are violated
		"""
		existing = self.get_by_id(document_id)
		if existing is None:
			return None

		# Recompute fingerprint in case content changed
		fingerprint = fingerprint_document(document)
		fingerprint_version = None
		if fingerprint != "empty":
			fingerprint_version = "v1"

		# Update fields
		existing.source_url = document.source_url
		existing.canonical_url = document.canonical_url
		existing.title = document.title
		existing.description = document.description
		existing.author = document.author
		existing.published_at = document.published_at
		existing.modified_at = document.modified_at
		existing.content = document.content
		existing.content_type = document.content_type
		existing.http_status = document.http_status
		existing.extraction_status = document.extraction_status.value
		existing.meta = document.metadata
		existing.fingerprint = fingerprint if fingerprint != "empty" else None
		existing.fingerprint_version = fingerprint_version

		try:
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except IntegrityError as e:
			self.session.rollback()
			raise e

	def upsert(
		self,
		document: PydanticDocument,
		source_id: int,
	) -> DocumentModel:
		"""
		Insert a document, or return the existing one if a duplicate fingerprint exists.

		If fingerprint is 'empty' or None, always creates a new document.

		Args:
			document: Pydantic Document
			source_id: Source ID for the document

		Returns:
			Persisted DocumentModel

		Raises:
			IntegrityError: If unique constraints fail for non-fingerprint reasons
		"""
		fingerprint = fingerprint_document(document)

		if fingerprint != "empty" and fingerprint is not None:
			existing = self.get_by_fingerprint(fingerprint)
			if existing is not None:
				return existing

		# No existing document with this fingerprint, create new
		return self.create(document, source_id)

	def delete(self, document_id: int) -> bool:
		"""
		Delete a document by ID.

		Returns:
			True if deleted, False if not found
		"""
		document = self.get_by_id(document_id)
		if document is None:
			return False

		self.session.delete(document)
		self.session.commit()
		return True

	def count(self) -> int:
		"""Return total number of documents."""
		stmt = select(DocumentModel)
		return len(self.session.scalars(stmt).all())

	def count_by_source(self, source_id: int) -> int:
		"""Return number of documents from a given source."""
		stmt = select(DocumentModel).where(DocumentModel.source_id == source_id)
		return len(self.session.scalars(stmt).all())


__all__ = ["DocumentRepository"]
