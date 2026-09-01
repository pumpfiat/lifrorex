from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas import ContentCreate, ContentUpdate
from app.models import Content, Knowledge
from app.models.content import (
	ContentCreationMethod,
	ContentDifficulty,
	ContentStatus,
	ContentType,
	content_knowledge,
)
from app.models.document import Document
from app.services.content_repository import ContentRepository


@pytest.fixture
def db_session() -> Session:
	engine = create_engine("sqlite:///:memory:")

	@event.listens_for(engine, "connect")
	def enable_foreign_keys(dbapi_connection, connection_record):
		dbapi_connection.execute("PRAGMA foreign_keys=ON")

	metadata = MetaData()
	Table("sources", metadata, Column("id", Integer, primary_key=True))
	metadata.create_all(engine)
	Document.__table__.create(engine)
	Knowledge.__table__.create(engine)
	Content.__table__.create(engine)
	content_knowledge.create(engine)

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=1))
	now = datetime.now(timezone.utc)
	session.add(
		Document(
			id=1,
			source_id=1,
			source_url="https://example.com/document",
			content="Source material.",
			extraction_status="success",
			meta={},
			created_at=now,
			updated_at=now,
		)
	)
	session.add_all(
		[
			Knowledge(id=1, document_id=1, knowledge_type="fact", content="First knowledge.", meta={}),
			Knowledge(id=2, document_id=1, knowledge_type="fact", content="Second knowledge.", meta={}),
			Knowledge(id=3, document_id=1, knowledge_type="fact", content="Third knowledge.", meta={}),
		]
	)
	session.commit()
	yield session
	session.close()


def glossary(title: str = "Pip", **overrides) -> ContentCreate:
	data = {
		"content_type": ContentType.GLOSSARY,
		"status": ContentStatus.DRAFT,
		"difficulty": ContentDifficulty.BEGINNER,
		"title": title,
		"body": "A learner-facing glossary explanation.",
		"payload": {"term": title, "definition": "A standard unit of price movement."},
		"creation_method": ContentCreationMethod.MANUAL,
		"knowledge_ids": [1],
	}
	data.update(overrides)
	return ContentCreate(**data)


def test_create_get_and_list_with_deterministic_filters(db_session):
	repository = ContentRepository(db_session)
	first = repository.create(glossary())
	second = repository.create(
		glossary(
			"Spread",
			status=ContentStatus.REVIEW,
			difficulty=ContentDifficulty.INTERMEDIATE,
			creation_method=ContentCreationMethod.RULE_BASED,
			knowledge_ids=[1, 2],
		)
	)

	assert repository.get_by_id(first.id).id == first.id
	assert repository.get_by_id(999) is None
	assert repository.list() == [first, second]
	assert repository.list(content_type=ContentType.GLOSSARY) == [first, second]
	assert repository.list(status=ContentStatus.REVIEW) == [second]
	assert repository.list(difficulty=ContentDifficulty.INTERMEDIATE) == [second]
	assert repository.list(creation_method=ContentCreationMethod.RULE_BASED) == [second]
	assert repository.list(knowledge_id=2) == [second]
	assert repository.list(limit=1, offset=1) == [second]
	with pytest.raises(ValueError):
		repository.list(limit=0)
	with pytest.raises(ValueError):
		repository.list(offset=-1)


def test_update_revalidates_typed_payload_and_replaces_knowledge_references(db_session):
	repository = ContentRepository(db_session)
	created = repository.create(glossary())

	updated = repository.update(
		created.id,
		ContentUpdate(
			title="Updated Pip",
			payload={"term": "Updated Pip", "definition": "An updated definition."},
			knowledge_ids=[2, 3],
		),
	)

	assert updated is not None
	assert updated.title == "Updated Pip"
	assert updated.payload == {"term": "Updated Pip", "definition": "An updated definition."}
	assert [knowledge.id for knowledge in updated.knowledge_records] == [2, 3]
	assert repository.update(999, ContentUpdate(title="Missing")) is None
	with pytest.raises(ValidationError):
		repository.update(created.id, ContentUpdate(payload={"prompt": "Wrong shape"}))
	assert repository.get_by_id(created.id).title == "Updated Pip"


def test_update_rejects_unknown_knowledge_without_partial_content_changes(db_session):
	repository = ContentRepository(db_session)
	created = repository.create(glossary())

	with pytest.raises(ValueError, match="existing Knowledge"):
		repository.update(created.id, ContentUpdate(title="Changed", knowledge_ids=[999]))

	persisted = repository.get_by_id(created.id)
	assert persisted.title == "Pip"
	assert [knowledge.id for knowledge in persisted.knowledge_records] == [1]


def test_content_type_is_immutable_and_lifecycle_operations_are_explicit(db_session):
	repository = ContentRepository(db_session)
	created = repository.create(glossary())

	with pytest.raises(ValidationError):
		ContentUpdate(content_type=ContentType.LESSON)
	assert repository.publish(created.id).status is ContentStatus.PUBLISHED
	assert repository.archive(created.id).status is ContentStatus.ARCHIVED
	assert repository.publish(999) is None
	assert repository.archive(999) is None
	assert db_session.scalars(select(Content)).one().id == created.id


def test_create_rejects_unknown_knowledge_without_creating_content(db_session):
	repository = ContentRepository(db_session)

	with pytest.raises(ValueError, match="existing Knowledge"):
		repository.create(glossary(knowledge_ids=[1, 999]))

	assert db_session.scalars(select(Content)).all() == []