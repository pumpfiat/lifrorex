import pytest
from pydantic import ValidationError

from app.api.schemas.knowledge import KnowledgeCreate
from app.knowledge.extraction import (
	KnowledgeCandidates,
	KnowledgeExtractionError,
	KnowledgeExtractor,
)
from app.models.document import Document


class FakeKnowledgeExtractor:
	def extract(self, document: Document) -> KnowledgeCandidates:
		return [
			KnowledgeCreate(
				document_id=document.id,
				knowledge_type="fact",
				content="Forex pairs are quoted as base and quote currencies.",
			),
			KnowledgeCreate(
				document_id=document.id,
				knowledge_type="concept",
				content="A pip measures a standardized price movement.",
			),
		]


@pytest.fixture
def document() -> Document:
	return Document(
		id=42,
		source_id=1,
		source_url="https://example.com/forex-basics",
		content="Forex basics content.",
		extraction_status="success",
		meta={},
	)


def test_extraction_contracts_import_and_construct_valid_candidates():
	candidates: KnowledgeCandidates = [
		KnowledgeCreate(
			document_id=42,
			knowledge_type="fact",
			content="A valid knowledge statement.",
		)
	]

	assert candidates[0].document_id == 42
	assert candidates[0].model_dump() == {
		"document_id": 42,
		"knowledge_type": "fact",
		"content": "A valid knowledge statement.",
		"meta": {},
		"evidence": None,
	}
	assert issubclass(KnowledgeExtractionError, Exception)


def test_extraction_candidates_reject_invalid_knowledge_data():
	with pytest.raises(ValidationError):
		KnowledgeCreate(document_id=0, knowledge_type="fact", content="Invalid provenance.")


def test_fake_extractor_matches_interface_and_preserves_document_provenance(document):
	extractor: KnowledgeExtractor = FakeKnowledgeExtractor()

	candidates = extractor.extract(document)

	assert len(candidates) == 2
	assert all(candidate.document_id == document.id for candidate in candidates)
	assert [candidate.knowledge_type for candidate in candidates] == ["fact", "concept"]