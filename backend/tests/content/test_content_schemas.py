import pytest
from pydantic import ValidationError

from app.api.schemas.content import (
	ConceptPayload,
	ContentCreate,
	GlossaryPayload,
	LessonPayload,
	QuestionPayload,
)
from app.models.content import (
	ContentCreationMethod,
	ContentDifficulty,
	ContentType,
)


def create_content(content_type: ContentType, payload: object, knowledge_ids: list[int] = [1]) -> ContentCreate:
	return ContentCreate(
		content_type=content_type,
		difficulty=ContentDifficulty.BEGINNER,
		title="Forex learning unit",
		body="A learner-facing explanation grounded in knowledge.",
		payload=payload,
		creation_method=ContentCreationMethod.MANUAL,
		knowledge_ids=knowledge_ids,
	)


@pytest.mark.parametrize(
	("content_type", "payload_type", "payload"),
	[
		(
			ContentType.CONCEPT,
			ConceptPayload,
			{"name": "Spread", "summary": "The difference between bid and ask prices."},
		),
		(
			ContentType.GLOSSARY,
			GlossaryPayload,
			{"term": "Pip", "definition": "A standard unit of price movement."},
		),
		(
			ContentType.LESSON,
			LessonPayload,
			{
				"introduction": "Learn how bid and ask prices create a spread.",
				"sections": [
					{"heading": "Bid and ask", "body": "The bid and ask are distinct market prices."},
					{"heading": "Calculation", "body": "Subtract the bid from the ask."},
				],
				"key_takeaways": ["Spread is the gap between two quoted prices."],
			},
		),
		(
			ContentType.QUESTION,
			QuestionPayload,
			{
				"prompt": "What does a pip measure?",
				"answer": "A standardized price movement.",
				"explanation": "Pips make small forex price changes comparable.",
				"options": ["Price movement", "Account balance"],
				"correct_option": 0,
			},
		),
	],
)
def test_content_type_accepts_only_its_valid_typed_payload(content_type, payload_type, payload):
	content = create_content(content_type, payload, knowledge_ids=[1, 2])

	assert isinstance(content.payload, payload_type)
	assert content.knowledge_ids == [1, 2]


@pytest.mark.parametrize(
	("content_type", "payload"),
	[
		(ContentType.CONCEPT, {"summary": "Missing a concept name."}),
		(ContentType.GLOSSARY, {"term": "Pip"}),
		(ContentType.LESSON, {"introduction": "Missing sections.", "sections": [], "key_takeaways": []}),
		(ContentType.QUESTION, {"prompt": "What is a pip?", "answer": "A price movement."}),
	],
)
def test_malformed_payloads_are_rejected(content_type, payload):
	with pytest.raises(ValidationError):
		create_content(content_type, payload)


@pytest.mark.parametrize(
	("content_type", "wrong_payload"),
	[
		(ContentType.CONCEPT, {"term": "Pip", "definition": "A price unit."}),
		(ContentType.GLOSSARY, {"name": "Pip", "summary": "A price unit."}),
		(ContentType.LESSON, {"prompt": "What is a pip?", "answer": "A price unit.", "explanation": "Explanation."}),
		(ContentType.QUESTION, {"introduction": "Introduction.", "sections": [{"heading": "One", "body": "Body."}], "key_takeaways": ["Takeaway."]}),
	],
)
def test_content_type_rejects_payload_for_another_type(content_type, wrong_payload):
	with pytest.raises(ValidationError):
		create_content(content_type, wrong_payload)


@pytest.mark.parametrize(
	"payload",
	[
		{
			"prompt": "Question?",
			"answer": "Answer.",
			"explanation": "Explanation.",
			"options": ["Only one"],
			"correct_option": 0,
		},
		{
			"prompt": "Question?",
			"answer": "Answer.",
			"explanation": "Explanation.",
			"options": ["One", "One"],
			"correct_option": 0,
		},
		{
			"prompt": "Question?",
			"answer": "Answer.",
			"explanation": "Explanation.",
			"options": ["One", "Two"],
			"correct_option": 2,
		},
	],
)
def test_question_options_are_structured_and_validated(payload):
	with pytest.raises(ValidationError):
		create_content(ContentType.QUESTION, payload)