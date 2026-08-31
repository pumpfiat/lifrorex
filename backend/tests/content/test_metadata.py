from datetime import datetime, timezone

from app.content import HtmlContentExtractor, MetadataExtractor


def test_title_description_canonical_author_and_dates_are_extracted() -> None:
	html = '''
<html>
  <head>
    <title>Primary Title</title>
    <meta name="description" content="Primary description" />
    <meta property="og:description" content="Fallback description" />
    <link rel="canonical" href="https://example.com/story" />
    <meta property="article:published_time" content="2026-08-20T10:30:00Z" />
    <meta property="article:modified_time" content="2026-08-21T11:45:00+00:00" />
    <meta name="author" content="Jane Doe" />
  </head>
  <body><h1>Market report</h1><p>Details</p></body>
</html>
'''
	metadata = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert metadata["title"] == "Primary Title"
	assert metadata["description"] == "Primary description"
	assert metadata["canonical_url"] == "https://example.com/story"
	assert metadata["author"] == "Jane Doe"
	assert metadata["published_at"] == datetime(2026, 8, 20, 10, 30, tzinfo=timezone.utc)
	assert metadata["modified_at"] == datetime(2026, 8, 21, 11, 45, tzinfo=timezone.utc)


def test_title_falls_back_to_og_title_when_missing() -> None:
	html = '''
<html>
  <head>
    <meta property="og:title" content="OpenGraph Title" />
  </head>
  <body>no title tag</body>
</html>
'''
	metadata = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert metadata["title"] == "OpenGraph Title"


def test_invalid_json_ld_is_ignored_without_crashing() -> None:
	html = '''
<html>
  <head>
    <title>Example</title>
    <script type="application/ld+json">{ invalid json </script>
  </head>
  <body>Content</body>
</html>
'''
	metadata = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert metadata["title"] == "Example"
	assert "json_ld" not in metadata["metadata"]


def test_json_ld_object_and_graph_are_supported() -> None:
	html = '''
<html>
  <head>
    <script type="application/ld+json">
      {"@type":"NewsArticle","headline":"Journal headline","description":"JsonLD description","datePublished":"2026-09-01T08:00:00Z","author":{"name":"Alice"},"url":"https://example.com/ld"}
    </script>
    <script type="application/ld+json">
      {"@graph":[{"@type":"Article","name":"Graph Title","dateModified":"2026-09-02T09:00:00Z"}]}
    </script>
  </head>
  <body>Body text</body>
</html>
'''
	metadata = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert metadata["title"] == "Journal headline"
	assert metadata["description"] == "JsonLD description"
	assert metadata["published_at"] == datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)
	assert metadata["author"] == "Alice"
	assert metadata["canonical_url"] == "https://example.com/ld"
	assert metadata["modified_at"] == datetime(2026, 9, 2, 9, 0, tzinfo=timezone.utc)


def test_invalid_date_and_url_are_ignored() -> None:
	html = '''
<html>
  <head>
    <meta property="article:published_time" content="not-a-date" />
    <link rel="canonical" href="not a valid url" />
  </head>
  <body>Content</body>
</html>
'''
	metadata = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert metadata.get("published_at") is None
	assert metadata.get("canonical_url") is None


def test_document_metadata_populates_document_fields() -> None:
	html = '''
<html>
  <head>
    <title>Document Title</title>
    <meta name="description" content="Document description" />
    <meta name="author" content="Writer" />
    <link rel="canonical" href="https://example.com/doc" />
  </head>
  <body><p>Visible content</p></body>
</html>
'''
	document = HtmlContentExtractor().extract_document(
		source_url="https://example.com/page",
		source_id=11,
		canonical_url="https://example.com/page",
		content_type="text/html",
		http_status=200,
		html=html,
	)
	assert document.title == "Document Title"
	assert document.description == "Document description"
	assert document.author == "Writer"
	assert document.canonical_url == "https://example.com/doc"
	assert document.source_id == 11
	assert document.source_url == "https://example.com/page"


def test_metadata_extraction_is_deterministic() -> None:
	html = '''
<html><head><title>Repeated Title</title><meta name="description" content="Repeated description" /></head><body>text</body></html>
'''
	first = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	second = MetadataExtractor().extract_metadata(html, "https://example.com/page")
	assert first == second
