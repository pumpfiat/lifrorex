from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.learning import LearningObjectiveCreate
from app.api.schemas.learning_sequence import LearningSequenceCreate, LearningSequenceItemCreate
from app.models import Knowledge
from app.models.content import ContentDifficulty
from app.models.document import Document
from app.models.learner_progress import LearnerObjectiveProgress, LearnerProgressStatus
from app.models.learning import (
	ContentPlan,
	LearningObjective,
	LearningProgression,
	learning_objective_knowledge,
	learning_objective_prerequisite,
)
from app.models.learning_sequence import LearningSequence, LearningSequenceItem
from app.services.learner_progress_repository import LearnerProgressRepository
from app.services.learner_progress_service import LearnerProgressError, LearnerProgressService
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
	ContentPlan.__table__.create(engine)
	LearningSequence.__table__.create(engine)
	LearningSequenceItem.__table__.create(engine)
	LearnerObjectiveProgress.__table__.create(engine)

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=1))
	now = datetime.now(timezone.utc)
	session.add(
		Document(
			id=1,
			source_id=1,
			source_url="https://example.com/forex",
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
			Knowledge(id=4, document_id=1, knowledge_type="fact", content="Fourth knowledge.", meta={}),
		]
	)
	session.commit()
	yield session
	session.close()


def create_objective(repository: LearningRepository, title: str, knowledge_id: int, prerequisites=None):
	return repository.create_objective(
		LearningObjectiveCreate(
			title=title,
			description=f"Learner can {title.lower()}.",
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.UNDERSTAND,
			knowledge_ids=[knowledge_id],
			prerequisite_ids=prerequisites or [],
		)
	)


def service(db_session):
	learning = LearningRepository(db_session)
	sequences = LearningSequenceRepository(db_session)
	return LearnerProgressService(LearnerProgressRepository(db_session), learning, sequences), learning, sequences


def test_progress_transitions_are_idempotent_and_completion_is_terminal(db_session):
	progress, learning, _ = service(db_session)
	objective = create_objective(learning, "Recognize a pip", 1)

	started = progress.start_objective(7, objective.id)
	assert started.status is LearnerProgressStatus.IN_PROGRESS
	assert started.started_at is not None
	assert progress.start_objective(7, objective.id).id == started.id
	completed = progress.complete_objective(7, objective.id)
	assert completed.status is LearnerProgressStatus.COMPLETED
	assert completed.completed_at is not None
	assert progress.complete_objective(7, objective.id).id == completed.id
	with pytest.raises(LearnerProgressError, match="cannot be restarted"):
		progress.start_objective(7, objective.id)
	assert len(LearnerProgressRepository(db_session).list(7)) == 1


def test_direct_completion_and_prerequisite_gating_are_deterministic(db_session):
	progress, learning, _ = service(db_session)
	prerequisite = create_objective(learning, "Recognize a pip", 1)
	dependent = create_objective(learning, "Calculate pip movement", 2, [prerequisite.id])

	with pytest.raises(LearnerProgressError, match="prerequisites"):
		progress.start_objective(9, dependent.id)
	assert progress.get_objective_progress(9, dependent.id) is None
	progress.complete_objective(9, prerequisite.id)
	assert progress.start_objective(9, dependent.id).status is LearnerProgressStatus.IN_PROGRESS
	assert progress.complete_objective(10, prerequisite.id).status is LearnerProgressStatus.COMPLETED


def test_sequence_progress_and_next_eligible_objective_are_derived(db_session):
	progress, learning, sequences = service(db_session)
	first = create_objective(learning, "Currency pairs", 1)
	second = create_objective(learning, "Bid and ask", 2, [first.id])
	third = create_objective(learning, "Spread", 3)
	fourth = create_objective(learning, "Pips", 4)
	sequence = sequences.create(
		LearningSequenceCreate(
			title="Forex foundations",
			description="Core ordered objectives.",
			difficulty=ContentDifficulty.BEGINNER,
		)
	)
	for position, objective in enumerate((first, second, third, fourth), 1):
		sequences.add_objective(
			sequence.id, LearningSequenceItemCreate(objective_id=objective.id, position=position)
		)

	progress.complete_objective(12, first.id)
	progress.complete_objective(12, second.id)
	progress.start_objective(12, third.id)
	state = progress.get_sequence_progress(12, sequence.id)

	assert (state.completed_count, state.total_count, state.percentage) == (2, 4, 50.0)
	assert state.next_objective_id == third.id
	progress.complete_objective(12, third.id)
	assert progress.get_next_objective(12, sequence.id) == fourth.id


def test_unknown_objective_and_repository_uniqueness_are_enforced(db_session):
	progress, _, _ = service(db_session)
	with pytest.raises(LearnerProgressError, match="not found"):
		progress.start_objective(1, 999)
	with pytest.raises(LearnerProgressError, match="not found"):
		progress.complete_objective(1, 999)
	assert LearnerProgressRepository(db_session).list(1) == []