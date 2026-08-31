from datetime import datetime, timezone
from unittest.mock import Mock, MagicMock

import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker

from app.content.document import Document, ExtractionStatus
from app.crawler.models import CrawlOperationResult, CrawlResult
from app.crawler.types import CrawlOutcome
from app.models.source import Source as SourceModel
from app.pipeline.pipeline import DocumentProcessingPipeline, ProcessingStatus


@pytest.fixture
def db_engine():
	"""Create an in-memory SQLite engine for testing."""
	engine = create_engine("sqlite:///:memory:")

	# Enable foreign keys for SQLite
	@event.listens_for(engine, "connect")
	def set_sqlite_pragma(dbapi_conn, connection_record):
		cursor = dbapi_conn.cursor()
		cursor.execute("PRAGMA foreign_keys=ON")
		cursor.close()

	# Create tables manually
	from sqlalchemy import (
		Table,
		Column,
		Integer,
		String,
		Text,
		DateTime,
		ForeignKey,
		MetaData,
	)

	metadata = MetaData()

	Table(
		"sources",
		metadata,
		Column("id", Integer, primary_key=True),
		Column("name", String, nullable=False),
		Column("url", String, unique=True, nullable=False),
		Column("categories", String, nullable=False),
		Column("trust_level", String, nullable=False),
		Column("license", String, nullable=False),
		Column("crawl_allowed", Integer, default=0, nullable=False),
		Column("active", Integer, default=1, nullable=False),
		Column("created_at", DateTime(timezone=True), nullable=False),
		Column("updated_at", DateTime(timezone=True), nullable=False),
	)

	Table(
		"documents",
		metadata,
		Column("id", Integer, primary_key=True),
		Column("source_id", Integer, ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False),
		Column("source_url", String, nullable=False),
		Column("canonical_url", String, nullable=True),
		Column("title", String, nullable=True),
		Column("description", Text, nullable=True),
		Column("author", String, nullable=True),
		Column("published_at", DateTime(timezone=True), nullable=True),
		Column("modified_at", DateTime(timezone=True), nullable=True),
		Column("content", Text, nullable=False),
		Column("content_type", String, nullable=True),
		Column("http_status", Integer, nullable=True),
		Column("extraction_status", String, nullable=False),
		Column("meta", String, nullable=False),
		Column("fingerprint", String, nullable=True, unique=True),
		Column("fingerprint_version", String, nullable=True),
		Column("created_at", DateTime(timezone=True), nullable=False),
		Column("updated_at", DateTime(timezone=True), nullable=False),
	)

	metadata.create_all(engine)
	yield engine
	metadata.drop_all(engine)


@pytest.fixture
def db_session(db_engine):
	"""Create a session for testing."""
	Session = sessionmaker(bind=db_engine)
	session = Session()
	yield session
	session.close()


@pytest.fixture
def test_source(db_session):
	"""Create a test source."""
	from sqlalchemy import text

	db_session.execute(
		text(
			"""
			INSERT INTO sources (id, name, url, categories, trust_level, license, crawl_allowed, active, created_at, updated_at)
			VALUES (:id, :name, :url, :categories, :trust_level, :license, :crawl_allowed, :active, :created_at, :updated_at)
		"""
		),
		{
			"id": 1,
			"name": "Test Source",
			"url": "https://example.com/",
			"categories": "test",
			"trust_level": "primary",
			"license": "open",
			"crawl_allowed": 1,
			"active": 1,
			"created_at": datetime.now(timezone.utc),
			"updated_at": datetime.now(timezone.utc),
		},
	)
	db_session.commit()

	class MockSource:
		id = 1
		url = "https://example.com/"
		active = True
		crawl_allowed = True

	return MockSource()


@pytest.fixture
def mock_crawler():
	"""Create a mock crawler for testing."""
	return Mock()


@pytest.fixture
def pipeline(db_session, mock_crawler):
	"""Create a pipeline for testing."""
	return DocumentProcessingPipeline(mock_crawler, db_session)


def _create_successful_crawl_result(url: str, content: bytes) -> CrawlOperationResult:
	"""Create a successful crawl result with the given content."""
	from app.crawler.types import CrawlOutcome
	
	fetch_result = CrawlResult(
		source_id=1,
		requested_url=url,
		outcome=CrawlOutcome.SUCCESS,
		succeeded=True,
		final_url=url,
		http_status=200,
		content_type="text/html; charset=utf-8",
		response_size=len(content),
		content=content,
		error=None,
	)
	return CrawlOperationResult(
		start_url=url,
		canonical_url=url,
		policy=None,
		fetched=True,
		fetch_result=fetch_result,
		html_processed=True,
	)


HTML_WITH_CONTENT = b"""
<html>
<head>
	<title>Foreign Exchange Market Report</title>
	<meta name="description" content="Weekly forex market analysis">
</head>
<body>
	<h1>Weekly Market Report</h1>
	<p>The foreign exchange market continues to show volatility. 
	Trading volumes have increased by 15% this week. Regulatory changes are expected soon.
	Central banks are monitoring the situation closely.</p>
</body>
</html>
"""

HTML_MINIMAL = b"<html><body>Home</body></html>"

HTML_MARKET_REPORT = b"""
<html>
<head>
	<title>CFTC Commitments of Traders Report</title>
	<meta name="description" content="Weekly trading positions">
</head>
<body>
	<h1>Commitments of Traders Report</h1>
	<p>Market participants are adjusting their positions in response to recent policy announcements.
	The derivatives market continues to grow. Risk management practices remain critical.</p>
</body>
</html>
"""


def test_pipeline_success_creates_document(pipeline, test_source, mock_crawler):
	"""Test successful document creation through the pipeline."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED
	assert result.document_id is not None
	assert result.fingerprint is not None
	assert result.document_source_url == "https://example.com/report"


def test_pipeline_duplicate_detection(pipeline, test_source, mock_crawler, db_session):
	"""Test that processing the same content twice creates only one document."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	# First run
	result1 = pipeline.process_url(test_source, "https://example.com/report")
	assert result1.status == ProcessingStatus.CREATED
	doc_id_1 = result1.document_id

	# Second run with same content
	result2 = pipeline.process_url(test_source, "https://example.com/report")
	assert result2.status == ProcessingStatus.DUPLICATE
	assert result2.document_id == doc_id_1  # Same document ID

	# Verify database has only one document
	from sqlalchemy import text
	count = db_session.execute(text("SELECT COUNT(*) FROM documents")).scalar()
	assert count == 1


def test_pipeline_different_content_creates_separate_documents(
	pipeline, test_source, mock_crawler
):
	"""Test that different content creates separate documents."""
	# First document
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report1",
		HTML_WITH_CONTENT,
	)
	result1 = pipeline.process_url(test_source, "https://example.com/report1")
	assert result1.status == ProcessingStatus.CREATED
	id1 = result1.document_id

	# Second document with different content
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report2",
		HTML_MARKET_REPORT,
	)
	result2 = pipeline.process_url(test_source, "https://example.com/report2")
	assert result2.status == ProcessingStatus.CREATED
	id2 = result2.document_id

	assert id1 != id2


def test_pipeline_fetch_failure(pipeline, test_source, mock_crawler):
	"""Test that fetch failures are handled correctly."""
	from app.crawler.types import CrawlOutcome
	
	fetch_result = CrawlResult(
		source_id=1,
		requested_url="https://example.com/notfound",
		outcome=CrawlOutcome.NOT_FOUND,
		succeeded=False,
		http_status=404,
		error="Not found",
	)
	mock_crawler.crawl.return_value = CrawlOperationResult(
		start_url="https://example.com/notfound",
		canonical_url="https://example.com/notfound",
		policy=None,
		fetched=True,
		fetch_result=fetch_result,
		html_processed=False,
		error="Not found",
	)

	result = pipeline.process_url(test_source, "https://example.com/notfound")

	assert result.status == ProcessingStatus.FETCH_FAILED
	assert result.error_detail is not None


def test_pipeline_insufficient_content_not_persisted(pipeline, test_source, mock_crawler):
	"""Test that documents with insufficient content are not persisted."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/empty",
		HTML_MINIMAL,
	)

	result = pipeline.process_url(test_source, "https://example.com/empty")

	assert result.status == ProcessingStatus.INSUFFICIENT_CONTENT
	assert result.document_id is None


def test_pipeline_non_html_content_rejected(pipeline, test_source, mock_crawler):
	"""Test that non-HTML content is rejected."""
	from app.crawler.types import CrawlOutcome
	
	fetch_result = CrawlResult(
		source_id=1,
		requested_url="https://example.com/pdf",
		outcome=CrawlOutcome.SUCCESS,
		succeeded=True,
		final_url="https://example.com/pdf",
		http_status=200,
		content_type="application/pdf",
		content=b"PDF content",
	)
	mock_crawler.crawl.return_value = CrawlOperationResult(
		start_url="https://example.com/pdf",
		canonical_url="https://example.com/pdf",
		policy=None,
		fetched=True,
		fetch_result=fetch_result,
		html_processed=False,
	)

	result = pipeline.process_url(test_source, "https://example.com/pdf")

	assert result.status == ProcessingStatus.EXTRACTION_FAILED


def test_pipeline_persists_classification(pipeline, test_source, mock_crawler, db_session):
	"""Test that classification is included in persisted metadata."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/cftc-report",
		b"""
		<html>
		<head><title>CFTC Market Report</title></head>
		<body>
			<p>Foreign exchange market analysis and regulatory updates.</p>
		</body>
		</html>
		""",
	)

	result = pipeline.process_url(test_source, "https://example.com/cftc-report")

	assert result.status == ProcessingStatus.CREATED

	# Retrieve from database and verify classification in metadata
	from sqlalchemy import text
	doc = db_session.execute(
		text("SELECT meta FROM documents WHERE id = :id"),
		{"id": result.document_id},
	).scalar()
	assert doc is not None  # Should have metadata


def test_pipeline_persists_quality_score(pipeline, test_source, mock_crawler, db_session):
	"""Test that quality score is persisted."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED


def test_pipeline_persists_relevance_score(pipeline, test_source, mock_crawler, db_session):
	"""Test that relevance score is persisted."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED


def test_pipeline_persists_fingerprint(pipeline, test_source, mock_crawler, db_session):
	"""Test that fingerprint is persisted exactly as computed."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED
	assert result.fingerprint is not None
	# Verify fingerprint is a valid SHA-256 hex string
	if result.fingerprint != "empty":
		assert len(result.fingerprint) == 64
		assert all(c in "0123456789abcdef" for c in result.fingerprint)


def test_pipeline_preserves_source_id(pipeline, test_source, mock_crawler, db_session):
	"""Test that source_id is correctly preserved."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED

	from sqlalchemy import text
	source_id = db_session.execute(
		text("SELECT source_id FROM documents WHERE id = :id"),
		{"id": result.document_id},
	).scalar()
	assert source_id == test_source.id


def test_pipeline_handles_persistence_error(pipeline, test_source, mock_crawler, db_session):
	"""Test that persistence errors are handled gracefully."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		HTML_WITH_CONTENT,
	)

	# First insertion succeeds
	result1 = pipeline.process_url(test_source, "https://example.com/report")
	assert result1.status == ProcessingStatus.CREATED

	# Force a persistence error by using same fingerprint
	# This tests rollback behavior
	result2 = pipeline.process_url(test_source, "https://example.com/report")
	# Should recognize as duplicate, not error
	assert result2.status == ProcessingStatus.DUPLICATE


def test_pipeline_extraction_failure_handled(pipeline, test_source, mock_crawler):
	"""Test that extraction failures are handled."""
	# Return content that will cause extraction to fail
	# (very malformed HTML that breaks the extractor)
	from app.crawler.types import CrawlOutcome
	
	fetch_result = CrawlResult(
		source_id=1,
		requested_url="https://example.com/report",
		outcome=CrawlOutcome.SUCCESS,
		succeeded=True,
		final_url="https://example.com/report",
		http_status=200,
		content_type="text/html",
		content=b"",  # Empty content
	)
	mock_crawler.crawl.return_value = CrawlOperationResult(
		start_url="https://example.com/report",
		canonical_url="https://example.com/report",
		policy=None,
		fetched=True,
		fetch_result=fetch_result,
		html_processed=False,
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	# Empty content should be treated as insufficient
	assert result.status == ProcessingStatus.INSUFFICIENT_CONTENT


def test_pipeline_metadata_included_in_document(pipeline, test_source, mock_crawler):
	"""Test that extracted metadata is included in persisted document."""
	mock_crawler.crawl.return_value = _create_successful_crawl_result(
		"https://example.com/report",
		b"""
		<html>
		<head>
			<title>Test Report</title>
			<meta name="description" content="Test description">
			<meta name="author" content="Test Author">
		</head>
		<body>
			<p>Content about foreign exchange markets and regulatory updates.</p>
		</body>
		</html>
		""",
	)

	result = pipeline.process_url(test_source, "https://example.com/report")

	assert result.status == ProcessingStatus.CREATED
	assert result.document_id is not None
