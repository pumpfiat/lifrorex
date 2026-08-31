from datetime import datetime, timezone

import pytest
from sqlalchemy import (
	create_engine,
	Integer,
	String,
	Text,
	DateTime,
	ForeignKey,
	Table,
	Column,
	MetaData,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.content.deduplication import fingerprint_document
from app.content.document import Document, ExtractionStatus
from app.models.document import Document as DocumentModel
from app.services.document_repository import DocumentRepository


class Base(DeclarativeBase):
	pass


@pytest.fixture
def db_engine():
	"""Create an in-memory SQLite engine for testing."""
	engine = create_engine("sqlite:///:memory:")

	# Enable foreign keys for SQLite
	from sqlalchemy import event
	@event.listens_for(engine, "connect")
	def set_sqlite_pragma(dbapi_conn, connection_record):
		cursor = dbapi_conn.cursor()
		cursor.execute("PRAGMA foreign_keys=ON")
		cursor.close()

	# Create only the sources and documents tables manually to avoid ARRAY type issues
	metadata = MetaData()

	sources_table = Table(
		"sources",
		metadata,
		Column("id", Integer, primary_key=True),
		Column("name", String, nullable=False),
		Column("url", String, unique=True, nullable=False),
		Column("categories", String, nullable=False),  # Simplified for SQLite
		Column("trust_level", String, nullable=False),
		Column("license", String, nullable=False),
		Column("crawl_allowed", Integer, default=0, nullable=False),
		Column("active", Integer, default=1, nullable=False),
		Column("created_at", DateTime(timezone=True), nullable=False),
		Column("updated_at", DateTime(timezone=True), nullable=False),
	)

	documents_table = Table(
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
		Column("meta", String, nullable=False),  # Simplified JSON
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
def cftc_source_data():
	"""Return test CFTC source data that can be inserted directly."""
	return {
		"id": 1,
		"name": "CFTC",
		"url": "https://www.cftc.gov/",
		"categories": "forex,markets,risk,regulation",
		"trust_level": "primary",
		"license": "government",
		"crawl_allowed": False,
		"active": True,
		"created_at": datetime.now(timezone.utc),
		"updated_at": datetime.now(timezone.utc),
	}


@pytest.fixture
def cftc_source(db_session, cftc_source_data):
	"""Create a test CFTC source using raw SQL."""
	from sqlalchemy import text

	stmt = text(
		"""
		INSERT INTO sources (id, name, url, categories, trust_level, license, crawl_allowed, active, created_at, updated_at)
		VALUES (:id, :name, :url, :categories, :trust_level, :license, :crawl_allowed, :active, :created_at, :updated_at)
	"""
	)
	db_session.execute(
		stmt,
		{
			"id": 1,
			"name": "CFTC",
			"url": "https://www.cftc.gov/",
			"categories": "forex,markets,risk,regulation",
			"trust_level": "primary",
			"license": "government",
			"crawl_allowed": 0,
			"active": 1,
			"created_at": datetime.now(timezone.utc),
			"updated_at": datetime.now(timezone.utc),
		},
	)
	db_session.commit()

	class MockSource:
		def __init__(self):
			self.id = 1

	return MockSource()



def test_create_valid_document(db_session, cftc_source):
	"""Test creating a valid document."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		title="Market Report",
		description="Commodity futures market report",
		content="Market summary for the week.",
	)

	persisted = repo.create(doc, cftc_source.id)

	assert persisted.id is not None
	assert persisted.source_id == cftc_source.id
	assert persisted.source_url == "https://www.cftc.gov/report"
	assert persisted.title == "Market Report"
	assert persisted.content == "Market summary for the week."
	assert persisted.fingerprint is not None
	assert persisted.fingerprint_version == "v1"
	assert persisted.created_at is not None
	assert persisted.updated_at is not None


def test_get_document_by_id(db_session, cftc_source):
	"""Test retrieving a document by ID."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Test content.",
	)
	persisted = repo.create(doc, cftc_source.id)

	retrieved = repo.get_by_id(persisted.id)

	assert retrieved is not None
	assert retrieved.id == persisted.id
	assert retrieved.source_url == "https://www.cftc.gov/report"


def test_get_document_by_fingerprint(db_session, cftc_source):
	"""Test retrieving a document by fingerprint."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Foreign exchange market report.",
	)
	persisted = repo.create(doc, cftc_source.id)
	fingerprint = persisted.fingerprint

	retrieved = repo.get_by_fingerprint(fingerprint)

	assert retrieved is not None
	assert retrieved.id == persisted.id


def test_duplicate_fingerprint_in_unique_constraint(db_session, cftc_source):
	"""Test that duplicate fingerprints violate the unique constraint."""
	repo = DocumentRepository(db_session)
	doc_a = Document(
		source_url="https://www.cftc.gov/report-a",
		content="Same content.",
	)
	doc_b = Document(
		source_url="https://www.cftc.gov/report-b",
		content="Same content.",
	)

	persisted_a = repo.create(doc_a, cftc_source.id)

	with pytest.raises(IntegrityError):
		repo.create(doc_b, cftc_source.id)


def test_different_fingerprints_are_separate_documents(db_session, cftc_source):
	"""Test that different fingerprints create separate documents."""
	repo = DocumentRepository(db_session)
	doc_a = Document(
		source_url="https://www.cftc.gov/report-a",
		content="Content A.",
	)
	doc_b = Document(
		source_url="https://www.cftc.gov/report-b",
		content="Content B.",
	)

	persisted_a = repo.create(doc_a, cftc_source.id)
	persisted_b = repo.create(doc_b, cftc_source.id)

	assert persisted_a.id != persisted_b.id
	assert persisted_a.fingerprint != persisted_b.fingerprint


def test_missing_source_fails_foreign_key(db_session):
	"""Test that documents cannot be created with a nonexistent source_id."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Test content.",
	)

	with pytest.raises(IntegrityError):
		repo.create(doc, source_id=9999)


def test_update_document_preserves_id_and_created_at(db_session, cftc_source):
	"""Test that updating a document preserves id and created_at."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		title="Original Title",
		content="Original content.",
	)
	persisted = repo.create(doc, cftc_source.id)
	original_id = persisted.id
	original_created_at = persisted.created_at

	updated_doc = Document(
		source_url="https://www.cftc.gov/report-updated",
		title="Updated Title",
		content="Updated content.",
	)
	updated = repo.update(original_id, updated_doc)

	assert updated is not None
	assert updated.id == original_id
	assert updated.created_at == original_created_at
	assert updated.title == "Updated Title"
	assert updated.content == "Updated content."


def test_update_changes_fingerprint_correctly(db_session, cftc_source):
	"""Test that updating content changes the fingerprint."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Original content.",
	)
	persisted = repo.create(doc, cftc_source.id)
	original_fingerprint = persisted.fingerprint

	updated_doc = Document(
		source_url="https://www.cftc.gov/report",
		content="New different content.",
	)
	updated = repo.update(persisted.id, updated_doc)

	assert updated is not None
	assert updated.fingerprint != original_fingerprint
	assert updated.content == "New different content."


def test_upsert_returns_existing_on_duplicate_fingerprint(db_session, cftc_source):
	"""Test that upsert returns existing document for duplicate fingerprint."""
	repo = DocumentRepository(db_session)
	doc_a = Document(
		source_url="https://www.cftc.gov/report-a",
		content="Same content.",
	)
	doc_b = Document(
		source_url="https://www.cftc.gov/report-b",
		content="Same content.",
	)

	persisted_a = repo.upsert(doc_a, cftc_source.id)
	persisted_b = repo.upsert(doc_b, cftc_source.id)

	assert persisted_a.id == persisted_b.id
	assert persisted_a.source_url == "https://www.cftc.gov/report-a"


def test_upsert_creates_new_on_different_fingerprint(db_session, cftc_source):
	"""Test that upsert creates new document for different fingerprint."""
	repo = DocumentRepository(db_session)
	doc_a = Document(
		source_url="https://www.cftc.gov/report-a",
		content="Content A.",
	)
	doc_b = Document(
		source_url="https://www.cftc.gov/report-b",
		content="Content B.",
	)

	persisted_a = repo.upsert(doc_a, cftc_source.id)
	persisted_b = repo.upsert(doc_b, cftc_source.id)

	assert persisted_a.id != persisted_b.id


def test_empty_fingerprint_documents_are_nullable(db_session, cftc_source):
	"""Test that documents with empty fingerprint are created with NULL fingerprint."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/empty",
		content="",
	)

	persisted = repo.create(doc, cftc_source.id)

	assert persisted.fingerprint is None
	assert persisted.fingerprint_version is None


def test_multiple_empty_fingerprint_documents_do_not_violate_uniqueness(
	db_session, cftc_source
):
	"""Test that multiple documents with NULL fingerprint can coexist."""
	repo = DocumentRepository(db_session)
	doc_a = Document(source_url="https://www.cftc.gov/empty-a", content="")
	doc_b = Document(source_url="https://www.cftc.gov/empty-b", content="")

	persisted_a = repo.create(doc_a, cftc_source.id)
	persisted_b = repo.create(doc_b, cftc_source.id)

	assert persisted_a.id != persisted_b.id
	assert persisted_a.fingerprint is None
	assert persisted_b.fingerprint is None


def test_get_all_by_source(db_session, cftc_source):
	"""Test retrieving all documents from a source."""
	repo = DocumentRepository(db_session)
	doc_a = Document(source_url="https://www.cftc.gov/a", content="A.")
	doc_b = Document(source_url="https://www.cftc.gov/b", content="B.")

	repo.create(doc_a, cftc_source.id)
	repo.create(doc_b, cftc_source.id)

	all_docs = repo.get_all_by_source(cftc_source.id)

	assert len(all_docs) == 2


def test_metadata_is_persisted(db_session, cftc_source):
	"""Test that metadata dict is persisted correctly."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Test.",
		metadata={"key": "value", "number": 42},
	)

	persisted = repo.create(doc, cftc_source.id)
	retrieved = repo.get_by_id(persisted.id)

	assert retrieved.meta == {"key": "value", "number": 42}


def test_classification_and_scores_persist(db_session, cftc_source):
	"""Test that classification and score data can be stored in metadata."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		content="Market report.",
		metadata={
			"classification": "market_report",
			"quality_score": 0.95,
			"relevance_score": 0.87,
		},
	)

	persisted = repo.create(doc, cftc_source.id)
	retrieved = repo.get_by_id(persisted.id)

	assert retrieved.meta["classification"] == "market_report"
	assert retrieved.meta["quality_score"] == 0.95
	assert retrieved.meta["relevance_score"] == 0.87


def test_document_does_not_mutate_original_pydantic(db_session, cftc_source):
	"""Test that persistence doesn't mutate the original Pydantic Document."""
	repo = DocumentRepository(db_session)
	doc = Document(
		source_url="https://www.cftc.gov/report",
		title="Title",
		content="Content.",
		metadata={"tag": "original"},
	)
	original_data = doc.model_dump()

	repo.create(doc, cftc_source.id)

	assert doc.model_dump() == original_data


def test_count_documents(db_session, cftc_source):
	"""Test counting total documents."""
	repo = DocumentRepository(db_session)
	doc_a = Document(source_url="https://www.cftc.gov/a", content="A.")
	doc_b = Document(source_url="https://www.cftc.gov/b", content="B.")

	repo.create(doc_a, cftc_source.id)
	repo.create(doc_b, cftc_source.id)

	assert repo.count() == 2


def test_count_by_source(db_session, cftc_source):
	"""Test counting documents from a specific source."""
	repo = DocumentRepository(db_session)
	doc_a = Document(source_url="https://www.cftc.gov/a", content="A.")
	doc_b = Document(source_url="https://www.cftc.gov/b", content="B.")

	repo.create(doc_a, cftc_source.id)
	repo.create(doc_b, cftc_source.id)

	assert repo.count_by_source(cftc_source.id) == 2


def test_delete_document(db_session, cftc_source):
	"""Test deleting a document."""
	repo = DocumentRepository(db_session)
	doc = Document(source_url="https://www.cftc.gov/report", content="Test.")

	persisted = repo.create(doc, cftc_source.id)
	assert repo.count() == 1

	deleted = repo.delete(persisted.id)
	assert deleted is True
	assert repo.count() == 0


def test_delete_nonexistent_document_returns_false(db_session):
	"""Test that deleting a nonexistent document returns False."""
	repo = DocumentRepository(db_session)
	deleted = repo.delete(9999)
	assert deleted is False


def test_transaction_rollback_on_integrity_error(db_session, cftc_source):
	"""Test that transaction rolls back correctly on integrity error."""
	repo = DocumentRepository(db_session)
	doc_a = Document(source_url="https://www.cftc.gov/a", content="Same.")
	doc_b = Document(source_url="https://www.cftc.gov/b", content="Same.")

	persisted_a = repo.create(doc_a, cftc_source.id)

	with pytest.raises(IntegrityError):
		repo.create(doc_b, cftc_source.id)

	# Session should still be usable
	doc_c = Document(source_url="https://www.cftc.gov/c", content="Different.")
	persisted_c = repo.create(doc_c, cftc_source.id)
	assert persisted_c.id is not None


def test_idempotent_upsert(db_session, cftc_source):
	"""Test that upserting the same document twice is idempotent."""
	repo = DocumentRepository(db_session)
	doc = Document(source_url="https://www.cftc.gov/report", content="Content.")

	persisted_1 = repo.upsert(doc, cftc_source.id)
	persisted_2 = repo.upsert(doc, cftc_source.id)

	assert persisted_1.id == persisted_2.id
	assert repo.count() == 1


def test_same_content_different_url_different_sources(db_session):
	"""Test that same content at different sources is recognized via fingerprint."""
	from sqlalchemy import text

	repo = DocumentRepository(db_session)

	# Create two sources using raw SQL
	db_session.execute(
		text(
			"""
			INSERT INTO sources (id, name, url, categories, trust_level, license, crawl_allowed, active, created_at, updated_at)
			VALUES (:id, :name, :url, :categories, :trust_level, :license, :crawl_allowed, :active, :created_at, :updated_at)
		"""
		),
		{
			"id": 1,
			"name": "Source A",
			"url": "https://example.com/a",
			"categories": "test",
			"trust_level": "primary",
			"license": "open",
			"crawl_allowed": 1,
			"active": 1,
			"created_at": datetime.now(timezone.utc),
			"updated_at": datetime.now(timezone.utc),
		},
	)
	db_session.execute(
		text(
			"""
			INSERT INTO sources (id, name, url, categories, trust_level, license, crawl_allowed, active, created_at, updated_at)
			VALUES (:id, :name, :url, :categories, :trust_level, :license, :crawl_allowed, :active, :created_at, :updated_at)
		"""
		),
		{
			"id": 2,
			"name": "Source B",
			"url": "https://example.com/b",
			"categories": "test",
			"trust_level": "secondary",
			"license": "open",
			"crawl_allowed": 1,
			"active": 1,
			"created_at": datetime.now(timezone.utc),
			"updated_at": datetime.now(timezone.utc),
		},
	)
	db_session.commit()

	# Create documents with same content from different sources
	doc_a = Document(
		source_url="https://example.com/a/report",
		content="Same content.",
	)
	doc_b = Document(
		source_url="https://example.com/b/report",
		content="Same content.",
	)

	persisted_a = repo.create(doc_a, 1)

	with pytest.raises(IntegrityError):
		# Same fingerprint, so unique constraint will fail
		repo.create(doc_b, 2)
