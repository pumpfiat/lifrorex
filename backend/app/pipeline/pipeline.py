from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.content import (
	Document,
	ExtractionStatus,
	classify_document,
	extract_document,
	extract_metadata,
	fingerprint_document,
	score_document,
)
from app.crawler.models import CrawlOperationResult
from app.crawler.orchestrator import SinglePageCrawlOrchestrator
from app.crawler.interfaces import CrawlSource
from app.models.source import Source as SourceModel
from app.services.document_repository import DocumentRepository


logger = logging.getLogger(__name__)


class ProcessingStatus(str, Enum):
	"""Result status from pipeline execution."""

	CREATED = "created"
	DUPLICATE = "duplicate"
	FETCH_FAILED = "fetch_failed"
	EXTRACTION_FAILED = "extraction_failed"
	PERSISTENCE_FAILED = "persistence_failed"
	INSUFFICIENT_CONTENT = "insufficient_content"


@dataclass(frozen=True)
class ProcessingResult:
	"""Result of pipeline execution."""

	status: ProcessingStatus
	document_id: Optional[int] = None
	document_source_url: Optional[str] = None
	fingerprint: Optional[str] = None
	error_detail: Optional[str] = None


class DocumentProcessingPipeline:
	"""Orchestrates the complete document processing pipeline.

	Coordinates crawling, extraction, classification, scoring, fingerprinting,
	deduplication, and persistence.

	This is an orchestrator that uses existing Step 8A-8G components without
	duplicating their logic.
	"""

	def __init__(
		self,
		crawler: SinglePageCrawlOrchestrator,
		database_session: Session,
	):
		"""
		Initialize the pipeline.

		Args:
			crawler: Configured crawl orchestrator for fetching content
			database_session: SQLAlchemy session for persistence
		"""
		self.crawler = crawler
		self.database_session = database_session
		self.repository = DocumentRepository(database_session)

	def process_url(
		self,
		source: SourceModel,
		url: str,
	) -> ProcessingResult:
		"""
		Process a URL through the complete pipeline.

		Flow:
		1. Crawl the URL
		2. Extract content
		3. Extract metadata
		4. Classify document
		5. Score quality and relevance
		6. Generate fingerprint
		7. Check for duplicates
		8. Persist to database

		Args:
			source: Source record (must exist in database)
			url: URL to process

		Returns:
			ProcessingResult with status and optional document ID
		"""
		# Step 1: Crawl
		logger.info(f"Pipeline: crawling {url} from source {source.id}")
		crawl_result = self.crawler.crawl(source, url)

		if not crawl_result.fetched or crawl_result.fetch_result is None:
			logger.warning(f"Pipeline: fetch failed for {url}: {crawl_result.error}")
			return ProcessingResult(
				status=ProcessingStatus.FETCH_FAILED,
				error_detail=crawl_result.error or "Unknown fetch failure",
			)

		if not crawl_result.fetch_result.succeeded:
			logger.warning(
				f"Pipeline: fetch unsuccessful for {url}: "
				f"status {crawl_result.fetch_result.http_status}"
			)
			return ProcessingResult(
				status=ProcessingStatus.FETCH_FAILED,
				error_detail=f"HTTP {crawl_result.fetch_result.http_status}",
			)

		# Check if we have usable HTML
		if not self._is_html(crawl_result.fetch_result.content_type):
			logger.warning(f"Pipeline: non-HTML content for {url}")
			return ProcessingResult(
				status=ProcessingStatus.EXTRACTION_FAILED,
				error_detail=f"Content type: {crawl_result.fetch_result.content_type}",
			)

		fetched_content_bytes = crawl_result.fetch_result.content
		fetched_url = crawl_result.fetch_result.final_url or url

		# Decode bytes to string
		try:
			fetched_content_html = fetched_content_bytes.decode("utf-8", errors="replace")
		except Exception as e:
			logger.error(f"Pipeline: failed to decode content from {fetched_url}: {e}")
			return ProcessingResult(
				status=ProcessingStatus.EXTRACTION_FAILED,
				error_detail=f"Content decode failed: {e}",
			)

		# Step 2: Extract content
		logger.info(f"Pipeline: extracting content from {fetched_url}")
		try:
			extracted_doc = extract_document(
				fetched_url,
				source_id=source.id,
				canonical_url=fetched_url,
				content_type=crawl_result.fetch_result.content_type,
				http_status=crawl_result.fetch_result.http_status,
				html=fetched_content_html,
			)
		except Exception as e:
			logger.error(f"Pipeline: extraction failed for {fetched_url}: {e}")
			return ProcessingResult(
				status=ProcessingStatus.EXTRACTION_FAILED,
				error_detail=str(e),
			)

		# Check for insufficient content
		if not extracted_doc.content or len(extracted_doc.content.strip()) < 10:
			logger.warning(f"Pipeline: insufficient content for {fetched_url}")
			return ProcessingResult(
				status=ProcessingStatus.INSUFFICIENT_CONTENT,
				document_source_url=fetched_url,
			)

		# Step 3: Extract metadata and merge into document
		logger.info(f"Pipeline: extracting metadata from {fetched_url}")
		try:
			metadata_dict = extract_metadata(fetched_content_html, fetched_url)
			# Apply metadata fields to document
			if "title" in metadata_dict and extracted_doc.title is None:
				extracted_doc.title = metadata_dict["title"]
			if "description" in metadata_dict and extracted_doc.description is None:
				extracted_doc.description = metadata_dict["description"]
			if "author" in metadata_dict and extracted_doc.author is None:
				extracted_doc.author = metadata_dict["author"]
			if "published_at" in metadata_dict and extracted_doc.published_at is None:
				extracted_doc.published_at = metadata_dict["published_at"]
			if "modified_at" in metadata_dict and extracted_doc.modified_at is None:
				extracted_doc.modified_at = metadata_dict["modified_at"]
			if "canonical_url" in metadata_dict:
				extracted_doc.canonical_url = metadata_dict["canonical_url"]
		except Exception as e:
			logger.error(f"Pipeline: metadata extraction failed for {fetched_url}: {e}")
			# Metadata extraction failure is not fatal; continue with extracted doc

		# Step 4: Classify
		logger.info(f"Pipeline: classifying document from {fetched_url}")
		classification = classify_document(extracted_doc)
		if classification:
			extracted_doc.metadata["classification"] = classification.document_type
			extracted_doc.metadata["classification_confidence"] = classification.confidence.value

		# Step 5: Score quality and relevance
		logger.info(f"Pipeline: scoring document from {fetched_url}")
		try:
			scores = score_document(extracted_doc)
			extracted_doc.metadata["quality_score"] = scores.quality
			extracted_doc.metadata["relevance_score"] = scores.relevance
			extracted_doc.metadata["quality_level"] = scores.quality_level
			extracted_doc.metadata["relevance_level"] = scores.relevance_level
		except Exception as e:
			logger.error(f"Pipeline: scoring failed for {fetched_url}: {e}")
			# Scoring failure is not fatal

		# Ensure extraction status is set
		extracted_doc.extraction_status = ExtractionStatus.SUCCESS

		# Step 6: Generate fingerprint
		logger.info(f"Pipeline: generating fingerprint for {fetched_url}")
		fingerprint = fingerprint_document(extracted_doc)

		# Step 7 & 8: Check for duplicates and persist
		logger.info(f"Pipeline: persisting document from {fetched_url}")
		try:
			# Check if a document with this fingerprint already exists
			existing_fingerprint = None
			if fingerprint != "empty":
				existing = self.repository.get_by_fingerprint(fingerprint)
				if existing is not None:
					existing_fingerprint = existing.fingerprint

			# Attempt to persist
			persisted = self.repository.upsert(extracted_doc, source.id)

			# Determine if this was a new document or a duplicate
			if existing_fingerprint is not None:
				# We found an existing document with this fingerprint before upsert
				logger.info(
					f"Pipeline: duplicate document detected, existing id {persisted.id}"
				)
				return ProcessingResult(
					status=ProcessingStatus.DUPLICATE,
					document_id=persisted.id,
					document_source_url=fetched_url,
					fingerprint=persisted.fingerprint,
				)
			else:
				# This was a new document
				logger.info(
					f"Pipeline: document created with id {persisted.id} from {fetched_url}"
				)
				return ProcessingResult(
					status=ProcessingStatus.CREATED,
					document_id=persisted.id,
					document_source_url=fetched_url,
					fingerprint=persisted.fingerprint,
				)

		except IntegrityError as e:
			logger.error(f"Pipeline: persistence failed for {fetched_url}: {e}")
			self.database_session.rollback()
			return ProcessingResult(
				status=ProcessingStatus.PERSISTENCE_FAILED,
				error_detail=str(e),
			)
		except Exception as e:
			logger.error(f"Pipeline: unexpected error during persistence: {e}")
			self.database_session.rollback()
			return ProcessingResult(
				status=ProcessingStatus.PERSISTENCE_FAILED,
				error_detail=str(e),
			)

	@staticmethod
	def _is_html(content_type: Optional[str]) -> bool:
		"""Check if content type is HTML."""
		if content_type is None:
			return False
		return "text/html" in content_type.lower()


__all__ = ["DocumentProcessingPipeline", "ProcessingResult", "ProcessingStatus"]
