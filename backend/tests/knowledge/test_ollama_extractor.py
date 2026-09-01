import json

import httpx
import pytest

from app.api.schemas.knowledge import KnowledgeCreate
from app.knowledge.extraction import KnowledgeExtractionError, KnowledgeExtractor
from app.knowledge.ollama import OllamaKnowledgeExtractor
from app.models.document import Document


@pytest.fixture
def document() -> Document:
	return Document(
		id=42,
		source_id=1,
		source_url="https://example.com/forex-basics",
		content="A pip is a standardized price movement in a currency pair.",
		extraction_status="success",
		meta={},
	)


def response_for(candidates: list[dict[str, object]]) -> httpx.Response:
	return httpx.Response(200, json={"message": {"content": json.dumps({"candidates": candidates})}})


def test_extracts_multiple_validated_candidates_with_configured_provider(document):
	requests: list[httpx.Request] = []

	def handler(request: httpx.Request) -> httpx.Response:
		requests.append(request)
		return response_for(
			[
				{
					"document_id": 999,
					"source_id": 123,
					"knowledge_type": "definition",
					"content": "A pip is a standardized price movement.",
					"evidence": {
						"document_id": 999,
						"source_id": 123,
						"text": "A pip is a standardized price movement in a currency pair.",
					},
				},
				{"knowledge_type": "concept", "content": "Currency pairs express one currency against another."},
			]
		)

	extractor: KnowledgeExtractor = OllamaKnowledgeExtractor(
		base_url="http://ollama.test:11434",
		model="test-model",
		transport=httpx.MockTransport(handler),
	)
	candidates = extractor.extract(document)

	assert all(isinstance(candidate, KnowledgeCreate) for candidate in candidates)
	assert [candidate.document_id for candidate in candidates] == [42, 42]
	assert len(candidates) == 2
	assert candidates[0].evidence is not None
	assert candidates[0].evidence.start_offset == 0
	assert candidates[0].evidence.end_offset == len(candidates[0].evidence.text)
	assert candidates[1].evidence is None
	assert requests[0].url == "http://ollama.test:11434/api/chat"
	request_body = json.loads(requests[0].content)
	assert request_body["model"] == "test-model"
	assert request_body["messages"][1]["content"] == document.content


def test_invalid_model_output_raises_provider_neutral_error(document):
	extractor = OllamaKnowledgeExtractor(
		transport=httpx.MockTransport(lambda request: response_for([{"knowledge_type": "fact"}]))
	)

	with pytest.raises(KnowledgeExtractionError):
		extractor.extract(document)


def test_connection_failure_raises_provider_neutral_error(document):
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ConnectError("unavailable", request=request)

	extractor = OllamaKnowledgeExtractor(transport=httpx.MockTransport(handler))

	with pytest.raises(KnowledgeExtractionError):
		extractor.extract(document)


def test_empty_extraction_returns_an_empty_candidate_list(document):
	extractor = OllamaKnowledgeExtractor(
		transport=httpx.MockTransport(lambda request: response_for([]))
	)

	assert extractor.extract(document) == []


def test_unrelated_evidence_raises_provider_neutral_error(document):
	extractor = OllamaKnowledgeExtractor(
		transport=httpx.MockTransport(
			lambda request: response_for(
				[
					{
						"knowledge_type": "fact",
						"content": "An unrelated statement.",
						"evidence": {"text": "This passage does not occur in the document."},
					}
				]
			)
		)
	)

	with pytest.raises(KnowledgeExtractionError):
		extractor.extract(document)