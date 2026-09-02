import json

import httpx
import pytest

from app.api.schemas.content import ConceptPayload, LessonPayload, QuestionPayload
from app.api.schemas.content_creation import ContentCreationSpec
from app.content.generation import ContentGenerationError, KnowledgeMaterial, OllamaContentGenerator
from app.models.content import ContentCreationMethod, ContentDifficulty, ContentStatus, ContentType
from app.models.learning import LearningProgression


MATERIAL = [
	KnowledgeMaterial(
		knowledge_id=10,
		content="A pip is a unit of price movement.",
		evidence=("A pip is a unit of price movement.",),
	),
	KnowledgeMaterial(
		knowledge_id=11,
		content="Pips make price changes comparable.",
		evidence=("Pips make price changes comparable.",),
	),
]


def spec(content_type: ContentType, fields: tuple[str, ...]) -> ContentCreationSpec:
	return ContentCreationSpec(
		content_plan_id=1,
		objective_id=2,
		content_type=content_type,
		difficulty=ContentDifficulty.BEGINNER,
		progression=LearningProgression.UNDERSTAND,
		sequence=1,
		title_guidance="Understand pips",
		objective_description="Explain what pips represent in price movement.",
		knowledge_ids=(10, 11),
		required_fields=fields,
	)


def transport(output: dict) -> httpx.MockTransport:
	return httpx.MockTransport(
		lambda request: httpx.Response(
			200, json={"message": {"content": json.dumps(output)}}, request=request
		)
	)


def output(payload: dict, evidence_id: int = 10, evidence_text: str = "A pip is a unit of price movement.") -> dict:
	return {
		"title": "Pips",
		"body": "A grounded learner-facing explanation.",
		"payload": payload,
		"supporting_evidence": [{"knowledge_id": evidence_id, "evidence_text": evidence_text}],
	}


@pytest.mark.parametrize(
	("content_type", "fields", "payload", "payload_class"),
	[
		(
			ContentType.CONCEPT,
			("name", "summary"),
			{"name": "Pip", "summary": "A unit for comparing price movement.", "key_points": ["Pips compare change."]},
			ConceptPayload,
		),
		(
			ContentType.LESSON,
			("introduction", "sections", "key_takeaways"),
			{
				"introduction": "Pips describe price movement.",
				"sections": [{"heading": "Pips", "body": "A pip is a unit of price movement."}],
				"key_takeaways": ["Pips make price movement comparable."],
			},
			LessonPayload,
		),
		(
			ContentType.QUESTION,
			("prompt", "answer", "explanation"),
			{
				"prompt": "What does a pip measure?",
				"answer": "A unit of price movement.",
				"explanation": "Pips make price changes comparable.",
				"options": ["Price movement", "Account balance"],
				"correct_option": 0,
			},
			QuestionPayload,
		),
	],
)
def test_generates_grounded_draft_for_each_new_content_type(content_type, fields, payload, payload_class):
	result = OllamaContentGenerator(transport=transport(output(payload))).generate(spec(content_type, fields), MATERIAL)

	assert result.content_type is content_type
	assert isinstance(result.payload, payload_class)
	assert result.knowledge_ids == [10, 11]
	assert result.status is ContentStatus.DRAFT
	assert result.creation_method is ContentCreationMethod.LLM_GENERATED


def test_rejects_wrong_payload_shape_and_mismatched_evidence_knowledge_id():
	concept_spec = spec(ContentType.CONCEPT, ("name", "summary"))
	lesson_payload = {
		"introduction": "Lesson introduction.",
		"sections": [{"heading": "Section", "body": "Body."}],
		"key_takeaways": ["Takeaway."],
	}
	with pytest.raises(ContentGenerationError):
		OllamaContentGenerator(transport=transport(output(lesson_payload))).generate(concept_spec, MATERIAL)

	concept_payload = {"name": "Pip", "summary": "A price unit."}
	with pytest.raises(ContentGenerationError, match="unsupported"):
		OllamaContentGenerator(
			transport=transport(output(concept_payload, evidence_id=11))
		).generate(concept_spec, MATERIAL)