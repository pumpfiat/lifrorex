from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.content import (
	ExtractionStatus,
	classify_document,
	extract_document,
	fingerprint_document,
	score_document,
)
from app.crawler.orchestrator import SinglePageCrawlOrchestrator
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
		2. Extract content (metadata -- title, description, author, dates,
		   canonical URL -- is extracted as part of this step; see
		   extract_document(), which already applies JSON-LD/Open-Graph/
		   plain-tag priority internally. A separate metadata-extraction pass
		   used to run again here, redundantly re-parsing the same HTML for
		   values that were already set)
		3. Classify document
		4. Score quality and relevance
		5. Generate fingerprint (for logging/observability)
		6. Persist to database (create-vs-duplicate is now decided
		   atomically inside upsert() -- a separate duplicate-check step used
		   to run first, which was both redundant and a race under
		   concurrent access; see document_repository.py's upsert())

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

		# Step 3: Classify
		# extract_document() in Step 2 already applied metadata (title,
		# description, author, dates, canonical_url) with correct
		# JSON-LD/Open-Graph/plain-tag priority. A separate metadata
		# extraction pass used to run here -- re-parsing the exact same HTML
		# with BeautifulSoup a second time, recomputing values that were
		# already set -- purely wasted work on every single document, since
		# every "if still None" check could never find anything new the
		# second time around. Removed rather than left as dead work.
		logger.info(f"Pipeline: classifying document from {fetched_url}")
		try:
			classification = classify_document(extracted_doc)
			if classification:
				extracted_doc.metadata["classification"] = classification.document_type
				extracted_doc.metadata["classification_confidence"] = classification.confidence.value
		except Exception as e:
			logger.error(f"Pipeline: classification failed for {fetched_url}: {e}")
			# Classification failure is not fatal; continue without it.
			# Previously this step had no try/except at all, unlike its
			# neighbors (metadata extraction, scoring) which both degrade
			# gracefully -- an unexpected error here would have crashed the
			# whole process_url() call for that URL instead of continuing.

		# Step 4: Score quality and relevance
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

		# Step 5: Generate fingerprint (for logging/observability -- upsert()
		# below computes its own fingerprint internally for the actual
		# duplicate-detection decision, since that logic belongs in the
		# repository layer, not passed in from the caller)
		fingerprint = fingerprint_document(extracted_doc)
		logger.info(f"Pipeline: fingerprint for {fetched_url} is {fingerprint}")

		# Step 6: Persist (upsert() now reports directly whether this was
		# a new document or an existing one with the same fingerprint, so the
		# separate pre-check that used to live here -- a second, redundant
		# get_by_fingerprint() query on every single document -- is gone.
		# See document_repository.py's upsert() for the full explanation of
		# why the old check-then-act pattern was also a race under
		# concurrent access, not just redundant.
		logger.info(f"Pipeline: persisting document from {fetched_url}")
		try:
			persisted, created = self.repository.upsert(extracted_doc, source.id)

			if created:
				logger.info(
					f"Pipeline: document created with id {persisted.id} from {fetched_url}"
				)
				return ProcessingResult(
					status=ProcessingStatus.CREATED,
					document_id=persisted.id,
					document_source_url=fetched_url,
					fingerprint=persisted.fingerprint,
				)
			else:
				logger.info(
					f"Pipeline: duplicate document detected, existing id {persisted.id}"
				)
				return ProcessingResult(
					status=ProcessingStatus.DUPLICATE,
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
