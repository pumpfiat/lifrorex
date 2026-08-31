from pathlib import Path

import pytest

from app.content import Document, ExtractionStatus, HtmlContentExtractor


FIXTURE = Path(__file__).with_name("fixtures").joinpath("financial_page.html")


def test_simple_html_extraction_filters_scripts_and_styles() -> None:
	html = FIXTURE.read_text(encoding="utf-8")
	text = HtmlContentExtractor().extract(html)
	assert "Market Report" in text
	assert "Markets moved higher today as risk appetite improved." in text
	assert "alert(\"secret\")" not in text
	assert "fetch(\"https://evil.example\")" not in text
	assert "body { font-family: sans-serif; }" not in text


def test_heading_paragraph_and_link_text_are_preserved() -> None:
	html = "<html><body><h1>Market Report</h1><p>Risk appetite improved.</p><a href=\"/report\">CFTC</a></body></html>"
	text = HtmlContentExtractor().extract(html)
	assert "Market Report" in text
	assert "Risk appetite improved." in text
	assert "CFTC" in text


def test_whitespace_is_normalized_and_entities_decoded() -> None:
	html = "<html><body><h1>Alpha &amp; Beta</h1><p>  White   space  </p></body></html>"
	text = HtmlContentExtractor().extract(html)
	assert "Alpha & Beta" in text
	assert "White space" in text
	assert "  " not in text


def test_empty_and_script_style_only_html_are_empty() -> None:
	assert HtmlContentExtractor().extract("") == ""
	assert HtmlContentExtractor().extract("<html><script>alert('x')</script><style>body{}</style></html>") == ""


def test_malformed_html_does_not_crash() -> None:
	html = "<div><h1>Market News<p>Markets moved higher<div>More content"
	text = HtmlContentExtractor().extract(html)
	assert "Market News" in text
	assert "Markets moved higher" in text
	assert "More content" in text


def test_table_text_is_preserved() -> None:
	html = "<table><tr><th>Date</th><th>Rate</th></tr><tr><td>2026-08-30</td><td>1.2456</td></tr></table>"
	text = HtmlContentExtractor().extract(html)
	assert "Date" in text
	assert "Rate" in text
	assert "2026-08-30" in text
	assert "1.2456" in text


def test_title_extraction_and_document_creation() -> None:
	html = "<html><head><title>Example Title</title></head><body><p>Hello</p></body></html>"
	document = HtmlContentExtractor().extract_document(
		source_url="https://example.com/page",
		source_id=7,
		canonical_url="https://example.com/page",
		content_type="text/html",
		http_status=200,
		html=html,
	)
	assert isinstance(document, Document)
	assert document.title == "Example Title"
	assert document.content == "Example Title\n\nHello"
	assert document.extraction_status is ExtractionStatus.SUCCESS
	assert document.source_id == 7
	assert document.source_url == "https://example.com/page"


def test_non_html_content_type_returns_unsupported() -> None:
	document = HtmlContentExtractor().extract_document(
		source_url="https://example.com/file.pdf",
		content_type="application/pdf",
		http_status=200,
		html="<html><body>ignored</body></html>",
	)
	assert document.extraction_status is ExtractionStatus.UNSUPPORTED
	assert document.content == ""
	assert document.title is None


def test_extraction_status_is_separate_from_http_status() -> None:
	document = HtmlContentExtractor().extract_document(
		source_url="https://example.com/page",
		http_status=200,
		content_type="text/html",
		html="<html><body><script>bad()</script></body></html>",
	)
	assert document.http_status == 200
	assert document.extraction_status is ExtractionStatus.SUCCESS


def test_deterministic_behavior_for_same_input() -> None:
	html = "<html><body><h1>Title</h1><p>  One  </p><p>Two</p></body></html>"
	assert HtmlContentExtractor().extract(html) == HtmlContentExtractor().extract(html)


def test_comments_are_removed() -> None:
	html = "<html><body><!-- hidden --><p>Visible content</p></body></html>"
	assert "hidden" not in HtmlContentExtractor().extract(html)
	assert "Visible content" in HtmlContentExtractor().extract(html)


def test_large_html_remains_readable() -> None:
	parts = "".join(f"<p>Paragraph {index}</p>" for index in range(200))
	html = f"<html><body>{parts}</body></html>"
	text = HtmlContentExtractor().extract(html)
	assert "Paragraph 0" in text
	assert "Paragraph 199" in text
	assert "<p>" not in text
