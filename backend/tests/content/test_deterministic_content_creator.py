from datetime import datetime, timezone

import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.api.schemas.content_creation import ContentCreationSpec
from app.api.schemas.learning import ContentPlanCreate, LearningObjectiveCreate
from app.content.creation import ContentCreationError, ContentCreator, DeterministicContentCreator
from app.models import Content, Knowledge
from app.models.content import (
	ContentCreationMethod,
	ContentDifficulty,
	ContentStatus,
	ContentType,
	content_knowledge,
)
from app.models.document import Document
from app.models.learning import (
	ContentPlan,
	LearningObjective,
	LearningProgression,
	learning_objective_knowledge,
	learning_objective_prerequisite,
)
from app.services.content_planning import ContentPlanningService
from app.services.content_repository import ContentRepository
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
	Content.__table__.create(engine)
	content_knowledge.create(engine)
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


def spec(content_type: ContentType, required_fields: tuple[str, ...]) -> ContentCreationSpec:
	return ContentCreationSpec(
		content_plan_id=1,
		objective_id=1,
		content_type=content_type,
		difficulty=ContentDifficulty.BEGINNER,
		progression=LearningProgression.INTRODUCE,
		sequence=1,
		title_guidance="Explain pip movement",
		objective_description="Explain what a pip represents in forex.",
		knowledge_ids=(1, 2),
		required_fields=required_fields,
	)


@pytest.mark.parametrize(
	("content_type", "required_fields", "material"),
	[
		(
			ContentType.CONCEPT,
			("name", "summary"),
			{"title": "Pip", "body": "A pip concept.", "name": "Pip", "summary": "A price movement unit."},
		),
		(
			ContentType.GLOSSARY,
			("term", "definition"),
			{"title": "Pip", "body": "A glossary entry.", "term": "Pip", "definition": "A price movement unit."},
		),
		(
			ContentType.LESSON,
			("introduction", "sections", "key_takeaways"),
			{
				"title": "Understanding pips",
				"body": "A short lesson.",
				"introduction": "Learn what a pip means.",
				"sections": [{"heading": "Pip", "body": "A pip measures price movement."}],
				"key_takeaways": ["Pips standardize price movement."],
			},
		),
		(
			ContentType.QUESTION,
			("prompt", "answer", "explanation"),
			{
				"title": "Pip question",
				"body": "Check pip understanding.",
				"prompt": "What is a pip?",
				"answer": "A price movement unit.",
				"explanation": "Pips standardize movement.",
				"options": ["A price unit", "A trade account"],
				"correct_option": 0,
			},
		),
	],
)
def test_creator_builds_each_typed_content_contract(content_type, required_fields, material):
	creator: ContentCreator = DeterministicContentCreator()

	content = creator.create(spec(content_type, required_fields), material)

	assert content.content_type is content_type
	assert content.status is ContentStatus.DRAFT
	assert content.creation_method is ContentCreationMethod.RULE_BASED
	assert content.knowledge_ids == [1, 2]


def test_creator_is_deterministic_and_does_not_persist(db_session):
	creator = DeterministicContentCreator()
	creation_spec = spec(ContentType.GLOSSARY, ("term", "definition"))
	material = {"title": "Pip", "body": "A glossary entry.", "term": "Pip", "definition": "A price movement unit."}

	first = creator.create(creation_spec, material)
	second = creator.create(creation_spec, material)

	assert first == second
	assert db_session.query(Content).count() == 0


def test_creator_rejects_missing_or_invalid_explicit_material():
	creator = DeterministicContentCreator()
	creation_spec = spec(ContentType.GLOSSARY, ("term", "definition"))
	with pytest.raises(ContentCreationError, match="missing required"):
		creator.create(creation_spec, {"title": "Pip", "body": "Entry.", "term": "Pip"})
	with pytest.raises(ContentCreationError, match="content contract"):
		creator.create(creation_spec, {"title": "Pip", "body": "Entry.", "term": "", "definition": "Definition."})
	with pytest.raises(ContentCreationError, match="spec"):
		creator.create(None, {})


def test_planning_to_creator_to_repository_preserves_knowledge_grounding(db_session):
	learning = LearningRepository(db_session)
	objective = learning.create_objective(
		LearningObjectiveCreate(
			title="Explain pip movement",
			description="Explain what a pip represents in forex.",
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.INTRODUCE,
			knowledge_ids=[1, 2],
		)
	)
	plan = learning.create_plan(
		ContentPlanCreate(
			objective_id=objective.id,
			content_type=ContentType.GLOSSARY,
			sequence=1,
			difficulty=ContentDifficulty.BEGINNER,
			progression=LearningProgression.INTRODUCE,
		)
	)
	creation_spec = ContentPlanningService(learning).create_spec_from_plan(plan.id)
	contract = DeterministicContentCreator().create(
		creation_spec,
		{"title": "Pip", "body": "A glossary entry.", "term": "Pip", "definition": "A price movement unit."},
	)
	persisted = ContentRepository(db_session).create(contract)

	assert persisted.status is ContentStatus.DRAFT
	assert persisted.creation_method is ContentCreationMethod.RULE_BASED
	assert [knowledge.id for knowledge in persisted.knowledge_records] == [1, 2]