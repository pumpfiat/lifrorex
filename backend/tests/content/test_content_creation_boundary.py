from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.learning import (
	ContentPlanCreate,
	LearningObjectiveCreate,
	LearningObjectiveUpdate,
)
from app.models import Knowledge
from app.models.content import ContentDifficulty, ContentStatus, ContentType
from app.models.document import Document
from app.models.learning import (
	ContentPlan,
	LearningObjective,
	LearningProgression,
	learning_objective_knowledge,
	learning_objective_prerequisite,
)
from app.services.content_planning import ContentPlanningError, ContentPlanningService
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
			Knowledge(id=2, document_id=1, knowledge_type="concept", content="Pips compare price movement.", meta={}),
		]
	)
	session.commit()
	yield session
	session.close()


def objective(repository: LearningRepository):
	return repository.create_objective(
		LearningObjectiveCreate(
			title="Explain pip movement",
			description="Explain what a pip represents in forex.",
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.INTRODUCE,
			status=ContentStatus.DRAFT,
			knowledge_ids=[1, 2],
		)
	)


@pytest.mark.parametrize(
	("content_type", "required_fields"),
	[
		(ContentType.CONCEPT, ("name", "summary")),
		(ContentType.GLOSSARY, ("term", "definition")),
		(ContentType.LESSON, ("introduction", "sections", "key_takeaways")),
		(ContentType.QUESTION, ("prompt", "answer", "explanation")),
	],
)
def test_plan_derives_deterministic_grounded_creation_spec(db_session, content_type, required_fields):
	repository = LearningRepository(db_session)
	objective_record = objective(repository)
	plan = repository.create_plan(
		ContentPlanCreate(
			objective_id=objective_record.id,
			content_type=content_type,
			sequence=1,
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.INTRODUCE,
		)
	)
	service = ContentPlanningService(repository)

	first = service.create_spec_from_plan(plan.id)
	second = service.create_spec_from_plan(plan.id)

	assert first == second
	assert first.content_plan_id == plan.id
	assert first.objective_id == objective_record.id
	assert first.knowledge_ids == (1, 2)
	assert first.required_fields == required_fields
	assert first.title_guidance == "Explain pip movement"
	assert first.objective_description == "Explain what a pip represents in forex."


def test_missing_plan_or_missing_objective_cannot_produce_a_spec(db_session):
	repository = LearningRepository(db_session)
	service = ContentPlanningService(repository)
	with pytest.raises(ContentPlanningError, match="was not found"):
		service.create_spec_from_plan(999)

	with pytest.raises(ValueError, match="existing LearningObjective"):
		LearningRepository(db_session).create_plan(
			ContentPlanCreate(
				objective_id=999,
				content_type=ContentType.GLOSSARY,
				sequence=1,
				difficulty=ContentDifficulty.BEGINNER,
				progression=LearningProgression.INTRODUCE,
			)
		)


def test_plan_and_objective_validation_reject_invalid_creation_inputs(db_session):
	repository = LearningRepository(db_session)
	with pytest.raises(ValueError, match="existing LearningObjective"):
		repository.create_plan(
			ContentPlanCreate(
				objective_id=999,
				content_type=ContentType.GLOSSARY,
				sequence=1,
				difficulty=ContentDifficulty.BEGINNER,
				progression=LearningProgression.INTRODUCE,
			)
		)

	objective_record = objective(repository)
	with pytest.raises(ValueError, match="existing Knowledge"):
		repository.update_objective(
			objective_record.id,
			LearningObjectiveUpdate(knowledge_ids=[999]),
		)