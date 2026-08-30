import pytest

from app.crawler.discovery import HtmlLinkDiscoverer
from app.crawler.exceptions import DiscoveryError
from app.crawler.urls import HttpUrlNormalizer, InMemoryUrlDeduplicator


@pytest.fixture
def discoverer() -> HtmlLinkDiscoverer:
	return HtmlLinkDiscoverer()


def test_discovers_and_resolves_supported_link_types_in_document_order(
	discoverer: HtmlLinkDiscoverer,
) -> None:
	html = """
		<a href="https://other.example.org/absolute">absolute</a>
		<a href="/root">root</a>
		<a href="report.html">relative</a>
		<a href="../reports/report.html">parent</a>
		<a href="//cdn.example.org/page">protocol relative</a>
	"""

	assert discoverer.discover(html.encode(), "https://example.com/research/index.html") == (
		"https://other.example.org/absolute",
		"https://example.com/root",
		"https://example.com/research/report.html",
		"https://example.com/reports/report.html",
		"https://cdn.example.org/page",
	)


def test_discovery_ignores_unsupported_empty_and_missing_hrefs(
	discoverer: HtmlLinkDiscoverer,
) -> None:
	html = """
		<a>missing</a><a href="">empty</a>
		<a href="javascript:void(0)">js</a><a href="mailto:test@example.com">mail</a>
		<a href="tel:+123456789">tel</a><a href="data:text/plain,test">data</a>
		<a href="ftp://example.com/file">ftp</a><a href="file:///tmp/file">file</a>
	"""

	assert discoverer.discover(html.encode(), "https://example.com/index.html") == ()


def test_discovery_handles_entities_case_whitespace_malformed_html_and_duplicates(
	discoverer: HtmlLinkDiscoverer,
) -> None:
	html = '<A HREF="  /search?q=forex&amp;region=global  ">one<a href="/search?q=forex&amp;region=global">two'

	assert discoverer.discover(html.encode(), "https://example.com/index.html") == (
		"https://example.com/search?q=forex&region=global",
	)


def test_first_valid_base_tag_changes_relative_resolution(discoverer: HtmlLinkDiscoverer) -> None:
	html = '<base href="/reports/"><base href="https://ignored.example/"><a href="annual.pdf">report</a>'
	assert discoverer.discover(html.encode(), "https://example.com/docs/index.html") == (
		"https://example.com/reports/annual.pdf",
	)


def test_absolute_base_and_invalid_base_behavior(discoverer: HtmlLinkDiscoverer) -> None:
	assert discoverer.discover(b'<base href="https://other.example/reports/"><a href="annual.pdf">', "https://example.com/docs/index.html") == (
		"https://other.example/reports/annual.pdf",
	)
	assert discoverer.discover(b'<base href="javascript:bad"><a href="annual.pdf">', "https://example.com/docs/index.html") == (
		"https://example.com/docs/annual.pdf",
	)


def test_discovery_leaves_fragments_for_step_7d_normalization(discoverer: HtmlLinkDiscoverer) -> None:
	candidate = discoverer.discover(b'<a href="HTTPS://EXAMPLE.COM/page#section">', "https://example.com/index.html")[0]
	assert candidate == "https://EXAMPLE.COM/page#section"
	assert HttpUrlNormalizer().normalize(candidate).canonical == "https://example.com/page"


def test_discovered_candidates_work_with_step_7d_deduplication(discoverer: HtmlLinkDiscoverer) -> None:
	candidates = discoverer.discover(
		b'<a href="/page"><a href="https://EXAMPLE.COM/page#section">',
		"https://example.com/index.html",
	)
	normalizer = HttpUrlNormalizer()
	deduplicator = InMemoryUrlDeduplicator()
	assert deduplicator.check_and_mark(normalizer.normalize(candidates[0])) is True
	assert deduplicator.check_and_mark(normalizer.normalize(candidates[1])) is False


def test_discovery_rejects_invalid_document_url(discoverer: HtmlLinkDiscoverer) -> None:
	with pytest.raises(DiscoveryError, match="document URL must be an absolute HTTP\\(S\\) URL"):
		discoverer.discover(b'<a href="/page">', "/relative-document")