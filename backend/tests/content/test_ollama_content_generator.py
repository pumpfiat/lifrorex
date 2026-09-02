import json

import httpx
import pytest

from app.api.schemas.content import GlossaryPayload
from app.api.schemas.content_creation import ContentCreationSpec
from app.content.generation import (
	ContentGenerationError,
	ContentGenerator,
	KnowledgeMaterial,
	OllamaContentGenerator,
)
from app.models.content import ContentCreationMethod, ContentDifficulty, ContentStatus, ContentType
from app.models.learning import LearningProgression


@pytest.fixture
def spec() -> ContentCreationSpec:
	return ContentCreationSpec(
		content_plan_id=1,
		objective_id=2,
		content_type=ContentType.GLOSSARY,
		difficulty=ContentDifficulty.BEGINNER,
		progression=LearningProgression.INTRODUCE,
		sequence=1,
		title_guidance="Explain a pip",
		objective_description="Explain what a pip represents.",
		knowledge_ids=(10,),
		required_fields=("term", "definition"),
	)


@pytest.fixture
def material() -> list[KnowledgeMaterial]:
	return [
		KnowledgeMaterial(
			knowledge_id=10,
			content="A pip is a unit of price movement.",
			evidence=("A pip is a unit of price movement.",),
		)
	]


def response(content: object) -> httpx.MockTransport:
	return httpx.MockTransport(
		lambda request: httpx.Response(200, json={"message": {"content": content}}, request=request)
	)


def valid_output() -> str:
	return json.dumps(
		{
			"title": "Pip",
			"body": "A glossary entry about a pip.",
			"payload": {"term": "Pip", "definition": "A unit of price movement."},
			"supporting_evidence": [{"knowledge_id": 10, "evidence_text": "A pip is a unit of price movement."}],
		}
	)


def test_generates_valid_grounded_glossary_with_configured_provider(spec, material):
	requests: list[httpx.Request] = []

	def handler(request: httpx.Request) -> httpx.Response:
		requests.append(request)
		return httpx.Response(200, json={"message": {"content": valid_output()}}, request=request)

	generator: ContentGenerator = OllamaContentGenerator(
		base_url="http://ollama.test:11434", model="configured-model", transport=httpx.MockTransport(handler)
	)
	result = generator.generate(spec, material)

	assert isinstance(result.payload, GlossaryPayload)
	assert result.knowledge_ids == [10]
	assert result.status is ContentStatus.DRAFT
	assert result.creation_method is ContentCreationMethod.LLM_GENERATED
	request_body = json.loads(requests[0].content)
	assert str(requests[0].url) == "http://ollama.test:11434/api/chat"
	assert request_body["model"] == "configured-model"


def test_rejects_invalid_json_and_invalid_glossary_schema(spec, material):
	with pytest.raises(ContentGenerationError):
		OllamaContentGenerator(transport=response("not json")).generate(spec, material)
	with pytest.raises(ContentGenerationError):
		OllamaContentGenerator(
			transport=response(json.dumps({"title": "Pip", "body": "Entry.", "payload": {"term": "Pip"}, "supporting_evidence": []}))
		).generate(spec, material)


def test_rejects_unsupported_evidence_and_missing_material_before_http(spec, material):
	unsupported = json.dumps(
		{
			"title": "Pip",
			"body": "Entry.",
			"payload": {"term": "Pip", "definition": "A unit of price movement."},
			"supporting_evidence": [{"knowledge_id": 10, "evidence_text": "Invented citation."}],
		}
	)
	with pytest.raises(ContentGenerationError, match="unsupported"):
		OllamaContentGenerator(transport=response(unsupported)).generate(spec, material)

	called = False
	def handler(request: httpx.Request) -> httpx.Response:
		nonlocal called
		called = True
		return httpx.Response(200, request=request)
	with pytest.raises(ContentGenerationError, match="material is required"):
		OllamaContentGenerator(transport=httpx.MockTransport(handler)).generate(spec, [])
	assert called is False


def test_converts_provider_failure_without_requiring_a_live_model(spec, material):
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ConnectError("unavailable", request=request)
	with pytest.raises(ContentGenerationError):
		OllamaContentGenerator(transport=httpx.MockTransport(handler)).generate(spec, material)


def test_same_response_and_inputs_produce_equal_validated_content_without_persistence(spec, material):
	generator = OllamaContentGenerator(transport=response(valid_output()))

	assert generator.generate(spec, material) == generator.generate(spec, material)