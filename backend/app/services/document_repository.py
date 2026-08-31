from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
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

	def get_all_by_source(
		self, source_id: int, limit: int = 100, offset: int = 0
	) -> list[DocumentModel]:
		"""Retrieve documents from a given source, paginated.

		Previously unbounded -- loaded every document from a source into
		memory in one query regardless of how many existed. At real volume
		("a lot of different documents") this would eventually mean loading
		an entire source's full document content into memory at once.
		Callers expecting literally every document should page through
		results (increasing offset) rather than assume this returns
		everything in one call.
		"""
		if limit <= 0:
			raise ValueError("limit must be positive")
		if offset < 0:
			raise ValueError("offset must be non-negative")
		stmt = (
			select(DocumentModel)
			.where(DocumentModel.source_id == source_id)
			.order_by(DocumentModel.id)
			.limit(limit)
			.offset(offset)
		)
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
	) -> tuple[DocumentModel, bool]:
		"""
		Insert a document, or return the existing one if a duplicate fingerprint exists.

		Returns (document, created) -- created is True if a new row was
		inserted, False if an existing document with the same fingerprint was
		found and returned instead.

		If fingerprint is 'empty' or None, always creates a new document (no
		exact-fingerprint deduplication is possible for content-less
		documents).

		Insert-first, not check-then-insert: previously this called
		get_by_fingerprint() to check for an existing row BEFORE attempting
		the insert -- a check-then-act race under concurrent access. Two
		workers processing identical content simultaneously could both pass
		the check before either had actually inserted, and the second
		worker's insert would then hit the unique constraint and raise
		IntegrityError, which the caller (the processing pipeline) would
		incorrectly report as a hard failure instead of the correct "this is
		a duplicate" outcome. This version lets the database's own unique
		constraint be the single source of truth: attempt the insert
		directly, and only on an actual conflict, look up what's already
		there. This also removes what used to be a redundant duplicate
		lookup -- callers no longer need their own separate pre-check just to
		learn whether the result was new or existing; this return value tells
		them directly.

		Args:
			document: Pydantic Document
			source_id: Source ID for the document

		Returns:
			(document, created) tuple

		Raises:
			IntegrityError: If a unique constraint fails for a reason OTHER
				than the fingerprint (e.g. a duplicate source_id+source_url)
				-- that's a genuine failure, not a duplicate, and is
				re-raised so it surfaces as one rather than being silently
				treated as a successful duplicate match.
		"""
		fingerprint = fingerprint_document(document)

		try:
			created_doc = self.create(document, source_id)
			return created_doc, True
		except IntegrityError:
			# create() already rolled back the session before re-raising, so
			# the session is clean and usable for the lookup below.
			if fingerprint != "empty" and fingerprint is not None:
				existing = self.get_by_fingerprint(fingerprint)
				if existing is not None:
					return existing, False
			# Either there's no fingerprint to deduplicate on, or a document
			# with this exact fingerprint genuinely doesn't exist -- the
			# conflict was caused by something else (e.g. source_id +
			# source_url). That's a real failure, not a duplicate; let the
			# caller see it rather than silently swallowing it.
			raise

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
		# Previously: select(DocumentModel) then len(...all()) -- loaded
		# every row's full content into memory just to return a number. At
		# real volume this is a genuine scalability failure, not a style nit.
		stmt = select(func.count()).select_from(DocumentModel)
		return self.session.scalar(stmt) or 0

	def count_by_source(self, source_id: int) -> int:
		"""Return number of documents from a given source."""
		stmt = (
			select(func.count())
			.select_from(DocumentModel)
			.where(DocumentModel.source_id == source_id)
		)
		return self.session.scalar(stmt) or 0


__all__ = ["DocumentRepository"]
