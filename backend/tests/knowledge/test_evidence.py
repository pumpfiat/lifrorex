import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import sessionmaker

from app.api.schemas import EvidenceCreate
from app.models import Evidence, Knowledge
from app.models.document import Document
from app.services.evidence_repository import EvidenceRepository


@pytest.fixture
def db_session():
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

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=7))
	document = Document(
		id=42,
		source_id=7,
		source_url="https://example.com/forex",
		content="A pip is a standardized unit of price movement in forex.",
		extraction_status="success",
		meta={},
		created_at=datetime.now(timezone.utc),
		updated_at=datetime.now(timezone.utc),
	)
	knowledge = Knowledge(
		id=3,
		document_id=42,
		knowledge_type="definition",
		content="A pip measures price movement.",
		meta={},
	)
	session.add_all([document, knowledge])
	session.commit()

	yield session
	session.close()


def test_evidence_persists_and_resolves_knowledge_document_source_chain(db_session):
	repository = EvidenceRepository(db_session)
	evidence_text = "A pip is a standardized unit of price movement in forex."
	evidence = repository.create(
		EvidenceCreate(
			knowledge_id=3,
			document_id=42,
			text=evidence_text,
			start_offset=0,
			end_offset=len(evidence_text),
		)
	)

	assert repository.get_by_knowledge_id(3) == [evidence]
	assert evidence.knowledge.id == 3
	assert evidence.document.id == 42
	assert evidence.document.source_id == 7


def test_evidence_can_support_canonical_knowledge_from_another_document(db_session):
	document = Document(
		id=2,
		source_id=7,
		source_url="https://example.com/second-document",
		content="A second document supports the same knowledge.",
		extraction_status="success",
		meta={},
		created_at=datetime.now(timezone.utc),
		updated_at=datetime.now(timezone.utc),
	)
	db_session.add(document)
	db_session.commit()

	evidence = EvidenceRepository(db_session).create(
		EvidenceCreate(
			knowledge_id=3,
			document_id=2,
			text="A second document supports the same knowledge.",
		)
	)

	assert evidence.knowledge_id == 3
	assert evidence.document_id == 2


def test_evidence_rejects_text_not_supported_by_its_document(db_session):
	with pytest.raises(ValueError, match="must occur"):
		EvidenceRepository(db_session).create(
			EvidenceCreate(knowledge_id=3, document_id=42, text="Unrelated passage.")
		)


def test_evidence_schema_requires_complete_valid_offsets():
	with pytest.raises(ValueError, match="supplied together"):
		EvidenceCreate(knowledge_id=3, document_id=42, text="Passage", start_offset=0)
	with pytest.raises(ValueError, match="greater"):
		EvidenceCreate(
			knowledge_id=3,
			document_id=42,
			text="Passage",
			start_offset=5,
			end_offset=5,
		)


def test_evidence_migration_is_syntactically_valid():
	migration_path = (
		Path(__file__).resolve().parents[2]
		/ "alembic"
		/ "versions"
		/ "e4f8a2c6b901_create_evidence_table.py"
	)
	spec = importlib.util.spec_from_file_location("evidence_migration", migration_path)
	assert spec is not None and spec.loader is not None
	migration = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(migration)

	assert migration.revision == "e4f8a2c6b901"
	assert migration.down_revision == "d3a1e9f4c702"