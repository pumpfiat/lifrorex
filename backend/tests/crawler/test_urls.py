import re

import pytest

from app.crawler.exceptions import UrlNormalizationError
from app.crawler.urls import HttpUrlNormalizer, InMemoryUrlDeduplicator


@pytest.fixture
def normalizer() -> HttpUrlNormalizer:
	return HttpUrlNormalizer()


@pytest.mark.parametrize(
	("raw_url", "canonical"),
	[
		("https://example.com/page", "https://example.com/page"),
		("HTTPS://EXAMPLE.COM/page", "https://example.com/page"),
		("https://example.com", "https://example.com/"),
		("http://example.com:80/page", "http://example.com/page"),
		("https://example.com:443/page", "https://example.com/page"),
		("https://example.com:8443/page", "https://example.com:8443/page"),
		("https://example.com/page#section", "https://example.com/page"),
		("https://example.com/page?", "https://example.com/page"),
		("https://example.com/a/./b", "https://example.com/a/b"),
		("https://example.com/a/../b", "https://example.com/b"),
		("https://example.com/a%2Fb", "https://example.com/a%2Fb"),
		("https://B\u00fccher.example/page", "https://xn--bcher-kva.example/page"),
	],
)
def test_normalize_produces_stable_canonical_url(
	normalizer: HttpUrlNormalizer, raw_url: str, canonical: str
) -> None:
	normalized = normalizer.normalize(raw_url)
	assert normalized.original == raw_url
	assert normalized.canonical == canonical
	assert normalizer.normalize(raw_url) == normalized


@pytest.mark.parametrize(
	("raw_url", "message"),
	[
		("ftp://example.com/file", "unsupported URL scheme"),
		("file:///tmp/test", "unsupported URL scheme"),
		("javascript:alert(1)", "unsupported URL scheme"),
		("/page", "absolute HTTP(S) URL required"),
		("../page", "absolute HTTP(S) URL required"),
		("page.html", "absolute HTTP(S) URL required"),
		("example.com/page", "absolute HTTP(S) URL required"),
		("https://user:password@example.com/page", "URL userinfo is not allowed"),
	],
)
def test_normalize_rejects_invalid_candidates_without_exposing_userinfo(
	normalizer: HttpUrlNormalizer, raw_url: str, message: str
) -> None:
	with pytest.raises(UrlNormalizationError, match=re.escape(message)) as error:
		normalizer.normalize(raw_url)
	assert "password" not in str(error.value)


def test_query_path_case_and_trailing_slash_remain_distinct(normalizer: HttpUrlNormalizer) -> None:
	assert normalizer.normalize("https://example.com/ABC").canonical != normalizer.normalize("https://example.com/abc").canonical
	assert normalizer.normalize("https://example.com/page").canonical != normalizer.normalize("https://example.com/page/").canonical
	assert normalizer.normalize("https://example.com/page?a=1&b=2").canonical == "https://example.com/page?a=1&b=2"
	assert normalizer.normalize("https://example.com/page?a=1&b=2").canonical != normalizer.normalize("https://example.com/page?b=2&a=1").canonical
	assert normalizer.normalize("https://example.com/page?a=1").canonical != normalizer.normalize("https://example.com/page?a=2").canonical


def test_deduplicator_uses_canonical_urls_not_raw_strings(normalizer: HttpUrlNormalizer) -> None:
	deduplicator = InMemoryUrlDeduplicator()
	for raw_url in ["https://example.com", "HTTPS://EXAMPLE.COM/#top", "https://example.com/#bottom"]:
		assert deduplicator.check_and_mark(normalizer.normalize(raw_url)) is (raw_url == "https://example.com")


def test_deduplicator_preserves_distinct_canonical_urls(normalizer: HttpUrlNormalizer) -> None:
	deduplicator = InMemoryUrlDeduplicator()
	urls = [
		"https://example.com/ABC",
		"https://example.com/abc",
		"https://example.com/page?a=1",
		"https://example.com/page?a=2",
		"https://example.com:8443/page",
		"https://other.example/page",
	]
	assert all(deduplicator.check_and_mark(normalizer.normalize(url)) for url in urls)
	assert deduplicator.is_seen(normalizer.normalize("https://example.com:8443/page")) is True