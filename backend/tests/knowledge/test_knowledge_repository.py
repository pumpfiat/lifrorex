from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas import KnowledgeCreate, KnowledgeUpdate
from app.models import Evidence, Knowledge
from app.services.knowledge_repository import KnowledgeRepository


class CountingSession(Session):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.commit_count = 0

	def commit(self):
		self.commit_count += 1
		return super().commit()


@pytest.fixture
def db_session():
	engine = create_engine("sqlite:///:memory:")

	@event.listens_for(engine, "connect")
	def enable_foreign_keys(dbapi_connection, connection_record):
		dbapi_connection.execute("PRAGMA foreign_keys=ON")

	metadata = MetaData()
	Table("sources", metadata, Column("id", Integer, primary_key=True))
	Table(
		"documents",
		metadata,
		Column("id", Integer, primary_key=True),
		Column("source_id", Integer, ForeignKey("sources.id"), nullable=False),
		Column("source_url", String, nullable=False),
		Column("content", String, nullable=False),
		Column("extraction_status", String, nullable=False),
		Column("meta", String, nullable=False),
		Column("created_at", DateTime(timezone=True), nullable=False),
		Column("updated_at", DateTime(timezone=True), nullable=False),
	)
	metadata.create_all(engine)
	Knowledge.__table__.create(engine)
	Evidence.__table__.create(engine)

	session = sessionmaker(bind=engine, class_=CountingSession)()
	now = datetime.now(timezone.utc)
	session.execute(metadata.tables["sources"].insert().values(id=1))
	session.execute(
		metadata.tables["documents"].insert(),
		[
			{
				"id": 1,
				"source_id": 1,
				"source_url": "https://example.com/one",
				"content": "Document one",
				"extraction_status": "complete",
				"meta": "{}",
				"created_at": now,
				"updated_at": now,
			},
			{
				"id": 2,
				"source_id": 1,
				"source_url": "https://example.com/two",
				"content": "Document two",
				"extraction_status": "complete",
				"meta": "{}",
				"created_at": now,
				"updated_at": now,
			},
		],
	)
	session.commit()
	session.commit_count = 0

	yield session
	session.close()


def create_knowledge(repository, document_id=1, content="Knowledge content."):
	return repository.create(
		KnowledgeCreate(
			document_id=document_id,
			knowledge_type="fact",
			content=content,
			meta={"origin": "test"},
		)
	)


def test_get_by_id_returns_existing_or_missing_knowledge(db_session):
	repository = KnowledgeRepository(db_session)
	persisted = create_knowledge(repository)

	assert repository.get_by_id(persisted.id) is persisted
	assert repository.get_by_id(999) is None


def test_get_by_document_id_filters_orders_limits_and_pages_results(db_session):
	repository = KnowledgeRepository(db_session)
	first = create_knowledge(repository, content="First.")
	second = create_knowledge(repository, content="Second.")
	create_knowledge(repository, document_id=2, content="Other document.")

	assert repository.get_by_document_id(1, limit=1) == [first]
	assert repository.get_by_document_id(1, limit=1, offset=1) == [second]
	assert repository.get_by_document_id(1, limit=10) == [first, second]
	assert repository.get_by_document_id(3) == []
	with pytest.raises(ValueError):
		repository.get_by_document_id(1, limit=0)
	with pytest.raises(ValueError):
		repository.get_by_document_id(1, offset=-1)


def test_create_persists_knowledge_with_generated_id(db_session):
	repository = KnowledgeRepository(db_session)

	persisted = create_knowledge(repository)

	assert persisted.id is not None
	assert persisted.document_id == 1
	assert persisted.meta == {"origin": "test"}
	assert persisted.created_at is not None
	assert persisted.updated_at is not None


def test_create_many_persists_records_with_one_commit(db_session):
	repository = KnowledgeRepository(db_session)

	persisted = repository.create_many(
		[
			KnowledgeCreate(document_id=1, knowledge_type="fact", content="First."),
			KnowledgeCreate(document_id=2, knowledge_type="concept", content="Second."),
		]
	)

	assert [item.id for item in persisted] == sorted(item.id for item in persisted)
	assert [item.content for item in persisted] == ["First.", "Second."]
	assert db_session.commit_count == 1
	assert repository.create_many([]) == []
	assert db_session.commit_count == 1


def test_update_applies_only_supplied_fields_and_handles_missing_ids(db_session):
	repository = KnowledgeRepository(db_session)
	persisted = create_knowledge(repository, content="Original.")

	updated = repository.update(persisted.id, KnowledgeUpdate(content="Updated."))

	assert updated is not None
	assert updated.content == "Updated."
	assert updated.document_id == 1
	assert updated.knowledge_type == "fact"
	assert updated.meta == {"origin": "test"}
	assert repository.update(999, KnowledgeUpdate(content="Missing.")) is None


def test_delete_removes_existing_knowledge_and_handles_missing_ids(db_session):
	repository = KnowledgeRepository(db_session)
	persisted = create_knowledge(repository)

	assert repository.delete(persisted.id) is True
	assert repository.get_by_id(persisted.id) is None
	assert repository.delete(persisted.id) is False


def test_create_or_get_reuses_canonical_duplicate_and_preserves_new_evidence(db_session):
	repository = KnowledgeRepository(db_session)
	canonical, created = repository.create_or_get(
		KnowledgeCreate(
			document_id=1,
			knowledge_type="fact",
			content="A pip is a unit of price movement.",
		)
	)
	duplicate, duplicate_created = repository.create_or_get(
		KnowledgeCreate(
			document_id=2,
			knowledge_type="fact",
			content=" A Pip Is A Unit Of Price Movement! ",
		)
	)

	assert created is True
	assert duplicate_created is False
	assert duplicate.id == canonical.id
	assert canonical.document_id == 1
	assert repository.get_by_fingerprint(canonical.fingerprint) == canonical
	assert len(repository.get_by_document_id(1)) == 1
	assert repository.get_by_document_id(2) == []

	assert Evidence.__table__.c.knowledge_id.references(Knowledge.__table__.c.id)


def test_create_or_get_keeps_related_but_different_knowledge_separate(db_session):
	repository = KnowledgeRepository(db_session)
	first, first_created = repository.create_or_get(
		KnowledgeCreate(
			document_id=1,
			knowledge_type="fact",
			content="Leverage allows traders to control larger positions.",
		)
	)
	second, second_created = repository.create_or_get(
		KnowledgeCreate(
			document_id=1,
			knowledge_type="fact",
			content="Leverage magnifies both potential gains and losses.",
		)
	)

	assert first_created is True
	assert second_created is True
	assert first.id != second.id
	assert first.fingerprint != second.fingerprint


def test_knowledge_fingerprint_is_required_and_uniquely_indexed(db_session):
	first = Knowledge(
		document_id=1,
		knowledge_type="fact",
		content="Identical content.",
		meta={},
	)
	second = Knowledge(
		document_id=2,
		knowledge_type="fact",
		content="Identical content.",
		meta={},
	)
	db_session.add(first)
	db_session.commit()
	db_session.add(second)

	with pytest.raises(Exception):
		db_session.commit()