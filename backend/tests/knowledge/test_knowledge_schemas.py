from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas import KnowledgeCreate, KnowledgeResponse, KnowledgeUpdate
from app.models import Knowledge


def test_knowledge_create_accepts_valid_data_and_metadata():
	knowledge = KnowledgeCreate(
		document_id=1,
		knowledge_type=" fact ",
		content=" A normalized knowledge statement. ",
		meta={"topics": ["forex"], "confidence": 0.9},
	)

	assert knowledge.document_id == 1
	assert knowledge.knowledge_type == "fact"
	assert knowledge.content == "A normalized knowledge statement."
	assert knowledge.meta == {"topics": ["forex"], "confidence": 0.9}


@pytest.mark.parametrize(
	"data",
	[
		{"knowledge_type": "fact", "content": "A fact."},
		{"document_id": 0, "knowledge_type": "fact", "content": "A fact."},
		{"document_id": -1, "knowledge_type": "fact", "content": "A fact."},
		{"document_id": 1, "content": "A fact."},
		{"document_id": 1, "knowledge_type": "", "content": "A fact."},
		{"document_id": 1, "knowledge_type": "   ", "content": "A fact."},
		{"document_id": 1, "knowledge_type": "fact"},
		{"document_id": 1, "knowledge_type": "fact", "content": ""},
		{"document_id": 1, "knowledge_type": "fact", "content": "   "},
		{"document_id": "invalid", "knowledge_type": "fact", "content": "A fact."},
		{"document_id": 1, "knowledge_type": ["fact"], "content": "A fact."},
		{"document_id": 1, "knowledge_type": "fact", "content": ["A fact."]},
		{"document_id": 1, "knowledge_type": "fact", "content": "A fact.", "meta": []},
	],
)
def test_knowledge_create_rejects_invalid_required_fields(data: dict[str, object]):
	with pytest.raises(ValidationError):
		KnowledgeCreate.model_validate(data)


def test_knowledge_create_defaults_meta_to_an_independent_empty_dictionary():
	first = KnowledgeCreate(document_id=1, knowledge_type="fact", content="First fact.")
	second = KnowledgeCreate(document_id=2, knowledge_type="fact", content="Second fact.")
	first.meta["source"] = "test"

	assert first.meta == {"source": "test"}
	assert second.meta == {}


def test_knowledge_update_allows_empty_and_partial_updates():
	assert KnowledgeUpdate().model_dump(exclude_unset=True) == {}

	update = KnowledgeUpdate(document_id=2)
	assert update.document_id == 2
	assert update.model_dump(exclude_unset=True) == {"document_id": 2}


def test_knowledge_update_rejects_invalid_updateable_values():
	with pytest.raises(ValidationError):
		KnowledgeUpdate(document_id=0)
	with pytest.raises(ValidationError):
		KnowledgeUpdate(knowledge_type=" ")
	with pytest.raises(ValidationError):
		KnowledgeUpdate(content=" ")
	with pytest.raises(ValidationError):
		KnowledgeUpdate(meta=[])
	with pytest.raises(ValidationError):
		KnowledgeUpdate(id=1)
	with pytest.raises(ValidationError):
		KnowledgeUpdate(created_at=datetime.now(timezone.utc))


def test_knowledge_response_converts_sqlalchemy_model_and_serializes_cleanly():
	now = datetime.now(timezone.utc)
	database_knowledge = Knowledge(
		id=1,
		document_id=2,
		knowledge_type="fact",
		content="A normalized knowledge statement.",
		meta={"topics": ["forex"]},
		created_at=now,
		updated_at=now,
	)

	response = KnowledgeResponse.model_validate(database_knowledge)

	assert response.id == 1
	assert response.document_id == 2
	assert response.knowledge_type == "fact"
	assert response.content == "A normalized knowledge statement."
	assert response.meta == {"topics": ["forex"]}
	assert response.created_at == now
	assert response.updated_at == now
	serialized = response.model_dump(mode="json")
	assert KnowledgeResponse.model_validate(serialized).created_at == now