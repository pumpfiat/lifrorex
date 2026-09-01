import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Column, DateTime, ForeignKey, Integer, MetaData, String, Table, create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.models import Knowledge
from app.models.document import Document


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

	session = sessionmaker(bind=engine)()
	session.execute(
		metadata.tables["sources"].insert().values(id=1)
	)
	session.execute(
		metadata.tables["documents"].insert().values(
			id=1,
			source_id=1,
			source_url="https://example.com/document",
			content="Document content",
			extraction_status="complete",
			meta="{}",
			created_at=datetime.now(timezone.utc),
			updated_at=datetime.now(timezone.utc),
		)
	)
	session.commit()

	yield session
	session.close()


def test_knowledge_model_imports_and_constructs():
	knowledge = Knowledge(
		document_id=1,
		knowledge_type="fact",
		content="A normalized knowledge statement.",
		meta={"confidence": "high", "topics": ["forex"]},
	)

	assert knowledge.document_id == 1
	assert knowledge.knowledge_type == "fact"
	assert knowledge.content == "A normalized knowledge statement."
	assert knowledge.meta == {"confidence": "high", "topics": ["forex"]}
	assert knowledge.fingerprint is None
	assert Knowledge.__table__.c.metadata.name == "metadata"


def test_knowledge_persists_required_fields_metadata_and_timestamps(db_session):
	knowledge = Knowledge(
		document_id=1,
		knowledge_type="fact",
		content="A normalized knowledge statement.",
		meta={"confidence": "high", "topics": ["forex"]},
	)
	db_session.add(knowledge)
	db_session.commit()
	db_session.refresh(knowledge)

	assert knowledge.id is not None
	assert knowledge.document_id == 1
	assert knowledge.knowledge_type == "fact"
	assert knowledge.content == "A normalized knowledge statement."
	assert knowledge.meta == {"confidence": "high", "topics": ["forex"]}
	assert knowledge.fingerprint is not None
	assert knowledge.created_at is not None
	assert knowledge.updated_at is not None


def test_knowledge_requires_document_id_content_and_knowledge_type(db_session):
	db_session.add(Knowledge(document_id=1, knowledge_type="fact", content=None))

	with pytest.raises(IntegrityError):
		db_session.commit()


def test_knowledge_document_foreign_key_targets_documents_table():
	foreign_key = next(iter(Knowledge.__table__.c.document_id.foreign_keys))

	assert foreign_key.target_fullname == "documents.id"
	assert Document.__tablename__ == "documents"


def test_knowledge_migration_is_syntactically_valid():
	migration_path = (
		Path(__file__).resolve().parents[2]
		/ "alembic"
		/ "versions"
		/ "d3a1e9f4c702_create_knowledge_table.py"
	)
	spec = importlib.util.spec_from_file_location("knowledge_migration", migration_path)
	assert spec is not None and spec.loader is not None
	migration = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(migration)

	assert migration.revision == "d3a1e9f4c702"
	assert migration.down_revision == "b2f4c91a7e3d"


def test_knowledge_fingerprint_migration_is_syntactically_valid():
	migration_path = (
		Path(__file__).resolve().parents[2]
		/ "alembic"
		/ "versions"
		/ "f5b9d3e7a014_add_knowledge_fingerprint.py"
	)
	spec = importlib.util.spec_from_file_location("fingerprint_migration", migration_path)
	assert spec is not None and spec.loader is not None
	migration = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(migration)

	assert migration.revision == "f5b9d3e7a014"
	assert migration.down_revision == "e4f8a2c6b901"