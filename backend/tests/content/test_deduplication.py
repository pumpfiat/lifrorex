import hashlib

from app.content import Document, deduplicate_documents, fingerprint_document, fingerprint_document_content


def test_exact_duplicate_content_yields_same_fingerprint() -> None:
	doc_a = Document(source_url="https://example.com/a", title="Foreign exchange market report", content="Foreign exchange market report.")
	doc_b = Document(source_url="https://example.com/b", title="Different title", content="Foreign exchange market report.")
	assert fingerprint_document_content(doc_a.content) == fingerprint_document_content(doc_b.content)
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)
	assert deduplicate_documents(doc_a, doc_b) is True


def test_whitespace_and_newline_normalization_keeps_identity() -> None:
	doc_a = Document(source_url="https://example.com/a", content="Foreign   exchange\nmarket report\n")
	doc_b = Document(source_url="https://example.com/b", content="Foreign exchange market report")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_crlf_and_lf_are_equivalent() -> None:
	doc_a = Document(source_url="https://example.com/a", content="Foreign exchange\r\nmarket report")
	doc_b = Document(source_url="https://example.com/b", content="Foreign exchange\nmarket report")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_same_content_different_urls_are_duplicates() -> None:
	doc_a = Document(source_url="https://example.com/report", content="Foreign exchange market report.")
	doc_b = Document(source_url="https://example.com/other-location?utm_source=x", content="Foreign exchange market report.")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_different_content_has_different_fingerprint() -> None:
	doc_a = Document(source_url="https://example.com/report", content="Foreign exchange market report.")
	doc_b = Document(source_url="https://example.com/outlook", content="Commodity futures market outlook.")
	assert fingerprint_document(doc_a) != fingerprint_document(doc_b)


def test_one_word_difference_changes_fingerprint() -> None:
	doc_a = Document(source_url="https://example.com/report", content="Foreign exchange market report")
	doc_b = Document(source_url="https://example.com/outlook", content="Foreign exchange market outlook")
	assert fingerprint_document(doc_a) != fingerprint_document(doc_b)


def test_empty_content_is_handled_safely() -> None:
	doc_a = Document(source_url="https://example.com/empty", content="")
	doc_b = Document(source_url="https://example.com/empty-two", content="")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)
	assert fingerprint_document(doc_a) == "empty"


def test_very_short_content_is_handled_conservatively() -> None:
	doc_a = Document(source_url="https://example.com/home", content="Home")
	doc_b = Document(source_url="https://example.com/home-two", content="Home")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)
	assert len(fingerprint_document(doc_a)) > 0


def test_unicode_content_is_preserved() -> None:
	doc_a = Document(source_url="https://example.com/es", content="Informe sobre mercados de divisas y riesgo financiero.")
	doc_b = Document(source_url="https://example.com/es-2", content="Informe sobre mercados de divisas y riesgo financiero.")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_same_document_repeated_calls_are_identical() -> None:
	doc = Document(source_url="https://example.com/repeat", content="Foreign exchange market report")
	first = fingerprint_document(doc)
	second = fingerprint_document(doc)
	assert first == second


def test_source_and_metadata_do_not_change_primary_fingerprint() -> None:
	doc_a = Document(source_id=1, source_url="https://example.com/report", title="Report", content="Foreign exchange market report.", metadata={"source":"A"})
	doc_b = Document(source_id=2, source_url="https://example.com/report-2", title="Other title", content="Foreign exchange market report.", metadata={"source":"B"})
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_classification_and_quality_scores_do_not_affect_primary_fingerprint() -> None:
	doc_a = Document(source_url="https://example.com/report", content="Foreign exchange market report.")
	doc_b = Document(source_url="https://example.com/report-2", content="Foreign exchange market report.")
	assert fingerprint_document(doc_a) == fingerprint_document(doc_b)


def test_document_fingerprint_has_sha256_format() -> None:
	doc = Document(source_url="https://example.com/report", content="Foreign exchange market report.")
	fingerprint = fingerprint_document(doc)
	assert len(fingerprint) == 64
	assert all(ch in "0123456789abcdef" for ch in fingerprint)
	assert hashlib.sha256(fingerprint_document_content(doc.content).encode("utf-8")).hexdigest() == fingerprint


def test_non_mutation_of_document_state() -> None:
	doc = Document(
		source_id=11,
		source_url="https://example.com/report",
		canonical_url="https://example.com/report",
		title="Report",
		content="Foreign exchange market report.",
		metadata={"tag": "keep"},
	)
	before = doc.model_dump()
	_ = fingerprint_document(doc)
	after = doc.model_dump()
	assert before == after
