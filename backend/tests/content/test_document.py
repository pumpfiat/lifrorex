import pytest
from pydantic import ValidationError

from app.content import Document, ExtractionStatus


def test_valid_minimal_document() -> None:
	document = Document(source_url="https://www.cftc.gov/")
	assert document.source_url == "https://www.cftc.gov/"
	assert document.canonical_url is None
	assert document.source_id is None
	assert document.title is None
	assert document.content == ""
	assert document.content_type is None
	assert document.http_status is None
	assert document.extraction_status is ExtractionStatus.PENDING


def test_valid_fully_populated_document() -> None:
	document = Document(
		source_id=1,
		source_url="https://www.cftc.gov/example",
		canonical_url="https://www.cftc.gov/example",
		title="Example Page",
		content="hello world",
		content_type="text/html",
		http_status=200,
		extraction_status=ExtractionStatus.SUCCESS,
		metadata={"language": "en"},
	)
	assert document.source_id == 1
	assert document.source_url == "https://www.cftc.gov/example"
	assert document.canonical_url == "https://www.cftc.gov/example"
	assert document.title == "Example Page"
	assert document.content == "hello world"
	assert document.content_type == "text/html"
	assert document.http_status == 200
	assert document.extraction_status is ExtractionStatus.SUCCESS
	assert document.metadata == {"language": "en"}


def test_document_preserves_provenance_through_round_trip() -> None:
	document = Document(
		source_id=1,
		source_url="https://www.cftc.gov/example",
		canonical_url="https://www.cftc.gov/example",
		content_type="application/pdf",
		http_status=200,
		extraction_status=ExtractionStatus.FAILED,
	)
	payload = document.model_dump()
	restored = Document.model_validate(payload)
	assert restored.source_id == 1
	assert restored.source_url == "https://www.cftc.gov/example"
	assert restored.canonical_url == "https://www.cftc.gov/example"
	assert restored.content_type == "application/pdf"
	assert restored.http_status == 200
	assert restored.extraction_status is ExtractionStatus.FAILED


def test_validates_urls_and_status_values() -> None:
	with pytest.raises(ValidationError):
		Document(source_url="not-a-url")
	with pytest.raises(ValidationError):
		Document(source_url="https://example.com", extraction_status="invalid")
	with pytest.raises(ValidationError):
		Document(source_url="https://example.com", source_id=0)
	with pytest.raises(ValidationError):
		Document(source_url="https://example.com", http_status=99)


def test_empty_text_and_optional_fields_are_handled() -> None:
	document = Document(source_url="https://example.com", title="  ", content="")
	assert document.title is None
	assert document.content == ""


def test_non_html_content_type_is_allowed() -> None:
	document = Document(
		source_url="https://example.com/file.json",
		content_type="application/json",
		extraction_status=ExtractionStatus.UNSUPPORTED,
	)
	assert document.content_type == "application/json"
	assert document.extraction_status is ExtractionStatus.UNSUPPORTED


def test_http_status_and_extraction_status_are_not_conflated() -> None:
	document = Document(
		source_url="https://example.com/page",
		http_status=200,
		extraction_status=ExtractionStatus.FAILED,
	)
	assert document.http_status == 200
	assert document.extraction_status is ExtractionStatus.FAILED


def test_serialization_and_deserialization_behavior() -> None:
	document = Document(
		source_id=42,
		source_url="https://example.com/source",
		canonical_url="https://example.com/source",
		title="Title",
		content="body",
		content_type="text/plain",
		http_status=200,
		extraction_status=ExtractionStatus.SUCCESS,
	)
	serialized = document.model_dump(mode="json")
	assert serialized["source_id"] == 42
	assert serialized["source_url"] == "https://example.com/source"
	assert serialized["extraction_status"] == "success"
	assert serialized["content_type"] == "text/plain"
	assert Document.model_validate(serialized).source_url == "https://example.com/source"
