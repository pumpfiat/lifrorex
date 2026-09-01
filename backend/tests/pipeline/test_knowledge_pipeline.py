from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas import EvidenceProposal, KnowledgeCreate
from app.knowledge.extraction import KnowledgeCandidates, KnowledgeExtractionError
from app.models import Evidence, Knowledge
from app.models.document import Document
from app.pipeline.knowledge_pipeline import (
	KnowledgeProcessingError,
	KnowledgeProcessingPipeline,
	KnowledgeProcessingStatus,
)


class FakeKnowledgeExtractor:
	def __init__(self, candidates_by_document_id: dict[int, KnowledgeCandidates]):
		self.candidates_by_document_id = candidates_by_document_id
		self.calls: list[int] = []

	def extract(self, document: Document) -> KnowledgeCandidates:
		self.calls.append(document.id)
		return self.candidates_by_document_id[document.id]


class FailingKnowledgeExtractor:
	def extract(self, document: Document) -> KnowledgeCandidates:
		raise KnowledgeExtractionError("test extraction failure")


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

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=7))
	now = datetime.now(timezone.utc)
	session.add_all(
		[
			Document(
				id=1,
				source_id=7,
				source_url="https://example.com/one",
				content="A pip is a unit of price movement. Leverage controls larger positions.",
				extraction_status="success",
				meta={},
				created_at=now,
				updated_at=now,
			),
			Document(
				id=2,
				source_id=7,
				source_url="https://example.com/two",
				content="A Pip Is A Unit Of Price Movement!",
				extraction_status="success",
				meta={},
				created_at=now,
				updated_at=now,
			),
			Document(
				id=3,
				source_id=7,
				source_url="https://example.com/empty",
				content="   ",
				extraction_status="success",
				meta={},
				created_at=now,
				updated_at=now,
			),
			Document(
				id=4,
				source_id=7,
				source_url="https://example.com/three",
				content="A pip is a unit of price movement.",
				extraction_status="success",
				meta={},
				created_at=now,
				updated_at=now,
			),
		]
	)
	session.commit()
	yield session
	session.close()


def candidate(document_id: int, content: str, evidence_text: str | None = None) -> KnowledgeCreate:
	evidence = EvidenceProposal(text=evidence_text) if evidence_text is not None else None
	return KnowledgeCreate(
		document_id=document_id,
		knowledge_type="fact",
		content=content,
		evidence=evidence,
	)


def test_pipeline_creates_knowledge_and_evidence_for_one_document(db_session):
	extractor = FakeKnowledgeExtractor(
		{1: [candidate(1, "A pip is a unit of price movement.", "A pip is a unit of price movement.")]}
	)

	result = KnowledgeProcessingPipeline(extractor, db_session).process_document(1)
	knowledge = db_session.scalars(select(Knowledge)).one()
	evidence = db_session.scalars(select(Evidence)).one()

	assert result.status is KnowledgeProcessingStatus.COMPLETED
	assert (result.extracted_count, result.created_count, result.duplicate_count) == (1, 1, 0)
	assert result.evidence_count == 1
	assert result.knowledge_ids == (knowledge.id,)
	assert knowledge.fingerprint
	assert evidence.knowledge_id == knowledge.id
	assert evidence.document_id == 1
	assert evidence.document.source_id == 7


def test_pipeline_processes_multiple_and_related_knowledge_independently(db_session):
	extractor = FakeKnowledgeExtractor(
		{
			1: [
				candidate(1, "Leverage allows traders to control larger positions."),
				candidate(1, "Leverage magnifies both potential gains and losses."),
			]
		}
	)

	result = KnowledgeProcessingPipeline(extractor, db_session).process_document(1)

	assert (result.extracted_count, result.created_count, result.duplicate_count) == (2, 2, 0)
	assert len(db_session.scalars(select(Knowledge)).all()) == 2


def test_pipeline_deduplicates_within_extraction_and_across_documents(db_session):
	extractor = FakeKnowledgeExtractor(
		{
			1: [
				candidate(1, "A pip is a unit of price movement.", "A pip is a unit of price movement."),
				candidate(1, "A Pip Is A Unit Of Price Movement!", "A pip is a unit of price movement."),
			],
			2: [candidate(2, "A Pip Is A Unit Of Price Movement!", "A Pip Is A Unit Of Price Movement!")],
		}
	)
	pipeline = KnowledgeProcessingPipeline(extractor, db_session)
	first = pipeline.process_document(1)
	second = pipeline.process_document(2)
	knowledge = db_session.scalars(select(Knowledge)).one()
	evidence = db_session.scalars(select(Evidence).order_by(Evidence.document_id)).all()

	assert (first.extracted_count, first.created_count, first.duplicate_count) == (2, 1, 1)
	assert (second.created_count, second.duplicate_count, second.evidence_count) == (0, 1, 1)
	assert first.knowledge_ids == (knowledge.id, knowledge.id)
	assert second.knowledge_ids == (knowledge.id,)
	assert [item.document_id for item in evidence] == [1, 2]


def test_pipeline_is_idempotent_and_handles_missing_empty_and_failed_extraction(db_session):
	extractor = FakeKnowledgeExtractor({1: [candidate(1, "A pip is a unit of price movement.")]})
	pipeline = KnowledgeProcessingPipeline(extractor, db_session)

	assert pipeline.process_document(1).created_count == 1
	assert pipeline.process_document(1).duplicate_count == 1
	assert len(db_session.scalars(select(Knowledge)).all()) == 1
	assert pipeline.process_document(3).status is KnowledgeProcessingStatus.EMPTY_DOCUMENT
	with pytest.raises(KnowledgeProcessingError, match="not found"):
		pipeline.process_document(999)
	with pytest.raises(KnowledgeProcessingError, match="failed"):
		KnowledgeProcessingPipeline(FailingKnowledgeExtractor(), db_session).process_document(2)
	assert extractor.calls == [1, 1]
	assert len(db_session.scalars(select(Knowledge)).all()) == 1


def test_repeated_documents_preserve_one_canonical_record_and_each_evidence(db_session):
	extractor = FakeKnowledgeExtractor(
		{
			1: [candidate(1, "A pip is a unit of price movement.", "A pip is a unit of price movement.")],
			2: [candidate(2, "A Pip Is A Unit Of Price Movement!", "A Pip Is A Unit Of Price Movement!")],
			4: [candidate(4, "A pip is a unit of price movement.", "A pip is a unit of price movement.")],
		}
	)
	pipeline = KnowledgeProcessingPipeline(extractor, db_session)

	for document_id in (1, 2, 4, 1, 2, 4):
		pipeline.process_document(document_id)

	assert len(db_session.scalars(select(Knowledge)).all()) == 1
	evidence = db_session.scalars(select(Evidence).order_by(Evidence.document_id)).all()
	assert [item.document_id for item in evidence] == [1, 2, 4]
	assert [item.document.source_id for item in evidence] == [7, 7, 7]


def test_invalid_extraction_and_persistence_failure_roll_back_all_changes(db_session):
	invalid_extractor = FakeKnowledgeExtractor(
		{1: [{"document_id": 1, "knowledge_type": "fact", "content": "   "}]}
	)
	with pytest.raises(KnowledgeProcessingError, match="failed"):
		KnowledgeProcessingPipeline(invalid_extractor, db_session).process_document(1)
	assert db_session.scalars(select(Knowledge)).all() == []
	assert db_session.scalars(select(Evidence)).all() == []

	failing_extractor = FakeKnowledgeExtractor(
		{1: [
			candidate(1, "A pip is a unit of price movement."),
			candidate(1, "Leverage controls larger positions.", "Not present in the document."),
		]}
	)
	with pytest.raises(KnowledgeProcessingError, match="failed"):
		KnowledgeProcessingPipeline(failing_extractor, db_session).process_document(1)
	assert db_session.scalars(select(Knowledge)).all() == []
	assert db_session.scalars(select(Evidence)).all() == []