from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.content import ContentCreate
from app.models import Content, Evidence, Knowledge
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
	Evidence.__table__.create(engine)
	Content.__table__.create(engine)
	content_knowledge.create(engine)

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=7))
	now = datetime.now(timezone.utc)
	document = Document(
		id=1,
		source_id=7,
		source_url="https://example.com/pip",
		content="A pip is a unit of price movement.",
		extraction_status="success",
		meta={},
		created_at=now,
		updated_at=now,
	)
	knowledge = [
		Knowledge(
			id=1,
			document_id=1,
			knowledge_type="definition",
			content="A pip is a unit of price movement.",
			meta={},
		),
		Knowledge(
			id=2,
			document_id=1,
			knowledge_type="concept",
			content="Currency pairs quote one currency against another.",
			meta={},
		),
	]
	session.add_all([document, *knowledge])
	session.commit()
	session.add(Evidence(knowledge_id=1, document_id=1, text=document.content))
	session.commit()
	yield session
	session.close()


def content_create(content_type: ContentType = ContentType.GLOSSARY, **overrides) -> ContentCreate:
	payloads = {
		ContentType.CONCEPT: {"name": "Pip", "summary": "A standard price movement."},
		ContentType.GLOSSARY: {
			"term": "Pip",
			"definition": "A standard unit of price movement.",
		},
		ContentType.LESSON: {
			"introduction": "Learn what a pip means.",
			"sections": [{"heading": "Definition", "body": "A pip measures price movement."}],
			"key_takeaways": ["A pip is a standard unit."],
		},
		ContentType.QUESTION: {
			"prompt": "What is a pip?",
			"answer": "A unit of price movement.",
			"explanation": "It standardizes small price changes.",
		},
	}
	data = {
		"content_type": content_type,
		"difficulty": ContentDifficulty.BEGINNER,
		"title": "Pip",
		"body": "A pip measures a small currency-pair price movement.",
		"payload": payloads.get(content_type, payloads[ContentType.GLOSSARY]),
		"creation_method": ContentCreationMethod.MANUAL,
		"knowledge_ids": [1],
	}
	data.update(overrides)
	return ContentCreate(**data)


@pytest.mark.parametrize("content_type", list(ContentType))
def test_content_schema_accepts_each_initial_content_type(content_type):
	assert content_create(content_type).content_type is content_type


@pytest.mark.parametrize("status", list(ContentStatus))
def test_content_schema_accepts_each_lifecycle_status(status):
	assert content_create(status=status).status is status


@pytest.mark.parametrize("difficulty", list(ContentDifficulty))
def test_content_schema_accepts_each_controlled_difficulty(difficulty):
	assert content_create(difficulty=difficulty).difficulty is difficulty


@pytest.mark.parametrize("method", list(ContentCreationMethod))
def test_content_schema_accepts_each_creation_method(method):
	assert content_create(creation_method=method).creation_method is method


def test_question_requires_structured_prompt_answer_and_explanation():
	with pytest.raises(ValidationError):
		content_create(ContentType.QUESTION, payload={})

	question = content_create(
		ContentType.QUESTION,
		payload={
			"prompt": "What is a pip?",
			"answer": "A unit of price movement.",
			"explanation": "It standardizes small price changes.",
		},
	)
	assert question.payload.prompt == "What is a pip?"


def test_content_references_multiple_knowledge_records_and_preserves_provenance(db_session):
	content = ContentRepository(db_session).create(
		content_create(
			ContentType.LESSON,
			status=ContentStatus.REVIEW,
			knowledge_ids=[1, 2],
			creation_method=ContentCreationMethod.RULE_BASED,
		)
	)

	assert content.id is not None
	assert content.status is ContentStatus.REVIEW
	assert [knowledge.id for knowledge in content.knowledge_records] == [1, 2]
	assert content.knowledge_records[0].content == "A pip is a unit of price movement."
	evidence = db_session.query(Evidence).filter_by(knowledge_id=1).one()
	assert evidence.document.id == 1
	assert evidence.document.source_id == 7


def test_content_creation_does_not_mutate_knowledge_or_require_ollama(db_session):
	knowledge = db_session.get(Knowledge, 1)
	original = (knowledge.content, knowledge.fingerprint, knowledge.document_id)

	ContentRepository(db_session).create(content_create(ContentType.CONCEPT))

	db_session.refresh(knowledge)
	assert (knowledge.content, knowledge.fingerprint, knowledge.document_id) == original


def test_content_rejects_invalid_enums_missing_knowledge_and_duplicate_references(db_session):
	with pytest.raises(ValidationError):
		content_create(
			content_type="article",
			payload={"term": "Pip", "definition": "A standard price movement."},
		)
	with pytest.raises(ValidationError):
		content_create(difficulty="expert")
	with pytest.raises(ValidationError):
		content_create(creation_method="automatic")
	with pytest.raises(ValueError, match="existing Knowledge"):
		ContentRepository(db_session).create(content_create(knowledge_ids=[999]))
	with pytest.raises(ValidationError, match="must not contain duplicates"):
		content_create(knowledge_ids=[1, 1])