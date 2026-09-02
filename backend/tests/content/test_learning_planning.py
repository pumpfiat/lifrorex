from datetime import datetime, timezone

import pytest
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.learning import (
	ContentPlanCreate,
	ContentPlanUpdate,
	LearningObjectiveCreate,
	LearningObjectiveUpdate,
)
from app.models import Evidence, Knowledge
from app.models.content import ContentDifficulty, ContentStatus, ContentType
from app.models.document import Document
from app.models.learning import (
	ContentPlan,
	LearningObjective,
	LearningProgression,
	learning_objective_knowledge,
	learning_objective_prerequisite,
)
from app.services.learning_repository import LearningRepository


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
	LearningObjective.__table__.create(engine)
	learning_objective_knowledge.create(engine)
	learning_objective_prerequisite.create(engine)
	ContentPlan.__table__.create(engine)

	session = sessionmaker(bind=engine)()
	session.execute(metadata.tables["sources"].insert().values(id=1))
	now = datetime.now(timezone.utc)
	session.add(
		Document(
			id=1,
			source_id=1,
			source_url="https://example.com/pips",
			content="A pip is a unit of price movement.",
			extraction_status="success",
			meta={},
			created_at=now,
			updated_at=now,
		)
	)
	session.add_all(
		[
			Knowledge(id=1, document_id=1, knowledge_type="definition", content="A pip is a unit of price movement.", meta={}),
			Knowledge(id=2, document_id=1, knowledge_type="concept", content="Pip movement can be calculated from two prices.", meta={}),
		]
	)
	session.commit()
	session.add(Evidence(knowledge_id=1, document_id=1, text="A pip is a unit of price movement."))
	session.commit()
	yield session
	session.close()


def objective_create(**overrides) -> LearningObjectiveCreate:
	data = {
		"title": "Calculate pip movement",
		"description": "Calculate the pip movement between two forex prices.",
		"difficulty": ContentDifficulty.BEGINNER,
		"progression": LearningProgression.APPLY,
		"status": ContentStatus.DRAFT,
		"knowledge_ids": [1, 2],
	}
	data.update(overrides)
	return LearningObjectiveCreate(**data)


def test_objective_is_grounded_in_knowledge_and_preserves_provenance(db_session):
	objective = LearningRepository(db_session).create_objective(objective_create())

	assert [knowledge.id for knowledge in objective.knowledge_records] == [1, 2]
	evidence = db_session.query(Evidence).filter_by(knowledge_id=1).one()
	assert evidence.document.source_id == 1


def test_objective_requires_known_unique_knowledge_and_valid_vocabularies(db_session):
	repository = LearningRepository(db_session)
	with pytest.raises(ValidationError):
		objective_create(knowledge_ids=[])
	with pytest.raises(ValidationError, match="duplicates"):
		objective_create(knowledge_ids=[1, 1])
	with pytest.raises(ValidationError):
		objective_create(progression="master")
	with pytest.raises(ValueError, match="existing Knowledge"):
		repository.create_objective(objective_create(knowledge_ids=[999]))
	assert repository.list_objectives() == []


def test_objective_prerequisites_and_updates_are_managed_deterministically(db_session):
	repository = LearningRepository(db_session)
	prerequisite = repository.create_objective(
		objective_create(title="Recognize a pip", progression=LearningProgression.RECOGNIZE)
	)
	objective = repository.create_objective(objective_create(prerequisite_ids=[prerequisite.id]))

	assert [item.id for item in repository.get_objective(objective.id).prerequisites] == [prerequisite.id]
	updated = repository.update_objective(
		objective.id,
		LearningObjectiveUpdate(knowledge_ids=[2], progression=LearningProgression.UNDERSTAND),
	)
	assert [knowledge.id for knowledge in updated.knowledge_records] == [2]
	assert updated.progression is LearningProgression.UNDERSTAND
	with pytest.raises(ValueError, match="own prerequisite"):
		repository.update_objective(objective.id, LearningObjectiveUpdate(prerequisite_ids=[objective.id]))
	assert repository.update_objective(999, LearningObjectiveUpdate(title="Missing")) is None


def test_content_plans_are_ordered_and_sequence_is_unique_per_objective(db_session):
	repository = LearningRepository(db_session)
	objective = repository.create_objective(objective_create())
	second = repository.create_plan(
		ContentPlanCreate(
			objective_id=objective.id,
			content_type=ContentType.LESSON,
			sequence=2,
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.UNDERSTAND,
		)
	)
	first = repository.create_plan(
		ContentPlanCreate(
			objective_id=objective.id,
			content_type=ContentType.GLOSSARY,
			sequence=1,
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.INTRODUCE,
		)
	)

	assert repository.list_plans(objective.id) == [first, second]
	with pytest.raises(ValueError, match="unique"):
		repository.create_plan(
			ContentPlanCreate(
				objective_id=objective.id,
				content_type=ContentType.QUESTION,
				sequence=1,
				difficulty=ContentDifficulty.BEGINNER,
				progression=LearningProgression.APPLY,
			)
		)
	updated = repository.update_plan(first.id, ContentPlanUpdate(sequence=3))
	assert updated.sequence == 3
	assert [plan.sequence for plan in repository.list_plans(objective.id)] == [2, 3]
	with pytest.raises(ValueError):
		repository.create_plan(
			ContentPlanCreate(
				objective_id=999,
				content_type=ContentType.CONCEPT,
				sequence=1,
				difficulty=ContentDifficulty.BEGINNER,
				progression=LearningProgression.INTRODUCE,
			)
		)