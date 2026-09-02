from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.learning import LearningObjectiveCreate
from app.api.schemas.learning_sequence import (
	LearningSequenceCreate,
	LearningSequenceItemCreate,
	LearningSequenceUpdate,
)
from app.models import Knowledge
from app.models.content import ContentDifficulty, ContentStatus
from app.models.document import Document
from app.models.learning import (
	LearningObjective,
	LearningProgression,
	learning_objective_knowledge,
	learning_objective_prerequisite,
)
from app.models.learning_sequence import LearningSequence, LearningSequenceItem
from app.services.learning_repository import LearningRepository
from app.services.learning_sequence_repository import LearningSequenceRepository


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
	LearningObjective.__table__.create(engine)
	learning_objective_knowledge.create(engine)
	learning_objective_prerequisite.create(engine)
	LearningSequence.__table__.create(engine)
	LearningSequenceItem.__table__.create(engine)

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=1))
	now = datetime.now(timezone.utc)
	session.add(
		Document(
			id=1,
			source_id=1,
			source_url="https://example.com/forex",
			content="Knowledge source.",
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


def objective(repository: LearningRepository, title: str, knowledge_id: int, prerequisite_ids=None):
	return repository.create_objective(
		LearningObjectiveCreate(
			title=title,
			description=f"Learner can {title.lower()}.",
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.UNDERSTAND,
			knowledge_ids=[knowledge_id],
			prerequisite_ids=prerequisite_ids or [],
		)
	)


def sequence_create(**overrides) -> LearningSequenceCreate:
	data = {
		"title": "Forex foundations",
		"description": "A deterministic introduction to forex foundations.",
		"difficulty": ContentDifficulty.BEGINNER,
	}
	data.update(overrides)
	return LearningSequenceCreate(**data)


def test_sequence_create_get_list_update_and_archive(db_session):
	repository = LearningSequenceRepository(db_session)
	created = repository.create(sequence_create())

	assert repository.get_by_id(created.id).id == created.id
	assert repository.get_by_id(999) is None
	assert repository.list() == [created]
	updated = repository.update(created.id, LearningSequenceUpdate(title="Forex basics"))
	assert updated.title == "Forex basics"
	assert repository.archive(created.id).status is ContentStatus.ARCHIVED
	assert repository.update(999, LearningSequenceUpdate(title="Missing")) is None
	assert repository.archive(999) is None


def test_objectives_are_ordered_reordered_and_removed_transactionally(db_session):
	learning = LearningRepository(db_session)
	first = objective(learning, "Recognize a pip", 1)
	second = objective(learning, "Calculate pip movement", 2, [first.id])
	third = objective(learning, "Interpret pips", 3)
	sequences = LearningSequenceRepository(db_session)
	sequence = sequences.create(sequence_create())

	sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=first.id, position=1))
	sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=second.id, position=2))
	sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=third.id, position=3))
	assert [item.objective_id for item in sequences.list_objectives(sequence.id)] == [first.id, second.id, third.id]
	reordered = sequences.reorder_objective(sequence.id, third.id, 2)
	assert reordered.position == 2
	assert [item.objective_id for item in sequences.list_objectives(sequence.id)] == [first.id, third.id, second.id]
	assert sequences.remove_objective(sequence.id, third.id) is True
	assert sequences.remove_objective(sequence.id, third.id) is False
	assert [item.objective_id for item in sequences.list_objectives(sequence.id)] == [first.id, second.id]


def test_duplicate_unknown_and_prerequisite_violating_sequence_items_are_rejected(db_session):
	learning = LearningRepository(db_session)
	prerequisite = objective(learning, "Recognize a pip", 1)
	dependent = objective(learning, "Calculate pip movement", 2, [prerequisite.id])
	third = objective(learning, "Interpret pips", 3)
	sequences = LearningSequenceRepository(db_session)
	sequence = sequences.create(sequence_create())

	with pytest.raises(ValueError, match="prerequisites"):
		sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=dependent.id, position=1))
	sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=prerequisite.id, position=1))
	sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=dependent.id, position=2))
	with pytest.raises(ValueError, match="duplicate"):
		sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=dependent.id, position=3))
	with pytest.raises(ValueError, match="duplicate"):
		sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=third.id, position=2))
	with pytest.raises(ValueError, match="existing LearningObjective"):
		sequences.add_objective(sequence.id, LearningSequenceItemCreate(objective_id=999, position=3))
	with pytest.raises(ValueError, match="existing LearningSequence"):
		sequences.list_objectives(999)
	with pytest.raises(ValueError, match="prerequisites"):
		sequences.reorder_objective(sequence.id, prerequisite.id, 2)
	assert [item.objective_id for item in sequences.list_objectives(sequence.id)] == [prerequisite.id, dependent.id]