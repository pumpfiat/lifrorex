from dataclasses import dataclass

from app.crawler.exceptions import DiscoveryError, UrlNormalizationError
from app.crawler.models import CrawlResult, PolicyDecision
from app.crawler.orchestrator import SinglePageCrawlOrchestrator
from app.crawler.types import CrawlOutcome, PolicyOutcome, PolicyReason
from app.crawler.urls import HttpUrlNormalizer, InMemoryUrlDeduplicator, NormalizedUrl


@dataclass
class FakeSource:
	id: int = 1
	url: str = "https://example.com/"
	active: bool = True
	crawl_allowed: bool = True


class RecordingNormalizer:
	def __init__(self, failures: set[str] | None = None) -> None:
		self.delegate = HttpUrlNormalizer()
		self.failures = failures or set()
		self.calls: list[str] = []

	def normalize(self, url: str) -> NormalizedUrl:
		self.calls.append(url)
		if url in self.failures:
			raise UrlNormalizationError("invalid")
		return self.delegate.normalize(url)


class RecordingDeduplicator:
	def __init__(self) -> None:
		self.delegate = InMemoryUrlDeduplicator()
		self.calls: list[str] = []

	def check_and_mark(self, url: NormalizedUrl) -> bool:
		self.calls.append(url.canonical)
		return self.delegate.check_and_mark(url)


class FakePolicy:
	def __init__(self, allowed: bool, events: list[str]) -> None:
		self.allowed = allowed
		self.events = events
		self.calls: list[str] = []

	def evaluate(self, source: FakeSource, url: str) -> PolicyDecision:
		self.events.append("policy")
		self.calls.append(url)
		return PolicyDecision(
			allowed=self.allowed,
			outcome=PolicyOutcome.ALLOWED if self.allowed else PolicyOutcome.DISALLOWED,
			reason=PolicyReason.ROBOTS_ALLOWED if self.allowed else PolicyReason.ROBOTS_DISALLOWED,
			url=url,
			source_id=source.id,
		)


class FakeFetcher:
	def __init__(self, result: CrawlResult, events: list[str]) -> None:
		self.result = result
		self.events = events
		self.calls: list[str] = []

	def fetch(self, url: str) -> CrawlResult:
		self.events.append("fetch")
		self.calls.append(url)
		return self.result


class FakeDiscoverer:
	def __init__(self, urls: tuple[str, ...], events: list[str], failure: bool = False) -> None:
		self.urls = urls
		self.events = events
		self.failure = failure
		self.calls: list[tuple[bytes, str]] = []

	def discover(self, content: bytes, base_url: str) -> tuple[str, ...]:
		self.events.append("discover")
		self.calls.append((content, base_url))
		if self.failure:
			raise DiscoveryError("bad HTML")
		return self.urls


def make_fetch_result(content_type: str = "text/html", content: bytes = b"<html></html>", succeeded: bool = True) -> CrawlResult:
	return CrawlResult(
		source_id=1,
		requested_url="https://example.com/",
		final_url="https://example.com/final",
		http_status=200 if succeeded else None,
		content_type=content_type,
		content=content,
		outcome=CrawlOutcome.SUCCESS if succeeded else CrawlOutcome.CONNECTION_ERROR,
		succeeded=succeeded,
		error=None if succeeded else "connection_error",
	)


def make_orchestrator(
	policy_allowed: bool = True,
	urls: tuple[str, ...] = (),
	fetch_result: CrawlResult | None = None,
	failures: set[str] | None = None,
	discovery_failure: bool = False,
) -> tuple[SinglePageCrawlOrchestrator, FakePolicy, FakeFetcher, FakeDiscoverer, list[str]]:
	events: list[str] = []
	policy = FakePolicy(policy_allowed, events)
	fetcher = FakeFetcher(fetch_result or make_fetch_result(), events)
	discoverer = FakeDiscoverer(urls, events, discovery_failure)
	orchestrator = SinglePageCrawlOrchestrator(
		RecordingNormalizer(failures), RecordingDeduplicator(), policy, fetcher, discoverer
	)
	return orchestrator, policy, fetcher, discoverer, events


def test_successful_html_crawl_composes_dependencies_in_order() -> None:
	orchestrator, policy, fetcher, discoverer, events = make_orchestrator(urls=("https://EXAMPLE.COM/page#one", "https://example.com/two"))
	result = orchestrator.crawl(FakeSource(), "HTTPS://EXAMPLE.COM/")
	assert events == ["policy", "fetch", "discover"]
	assert policy.calls == ["https://example.com/"]
	assert fetcher.calls == ["https://example.com/"]
	assert discoverer.calls == [(b"<html></html>", "https://example.com/final")]
	assert result.candidates == ("https://example.com/page", "https://example.com/two")
	assert result.error is None


def test_policy_denial_prevents_fetch_and_discovery() -> None:
	orchestrator, _, fetcher, discoverer, events = make_orchestrator(policy_allowed=False)
	result = orchestrator.crawl(FakeSource(), "https://example.com/")
	assert events == ["policy"]
	assert fetcher.calls == []
	assert discoverer.calls == []
	assert result.fetched is False
	assert result.policy is not None and result.policy.allowed is False


def test_fetch_failure_and_non_html_skip_discovery() -> None:
	failure, _, failing_fetcher, failing_discoverer, _ = make_orchestrator(fetch_result=make_fetch_result(succeeded=False))
	failure_result = failure.crawl(FakeSource(), "https://example.com/")
	assert failure_result.error == "connection_error"
	assert failing_discoverer.calls == []
	non_html, _, _, non_html_discoverer, _ = make_orchestrator(fetch_result=make_fetch_result("application/pdf"))
	non_html_result = non_html.crawl(FakeSource(), "https://example.com/")
	assert non_html_result.fetched is True and non_html_result.html_processed is False
	assert non_html_discoverer.calls == []
	assert failing_fetcher.calls == ["https://example.com/"]


def test_discovered_duplicates_invalid_links_self_links_and_cross_domain_are_classified() -> None:
	orchestrator, _, fetcher, _, _ = make_orchestrator(
		urls=("https://example.com/", "HTTPS://EXAMPLE.COM/page#section", "https://example.com/page", "javascript:void(0)", "https://other.example.org/page")
	)
	result = orchestrator.crawl(FakeSource(), "https://example.com/")
	assert fetcher.calls == ["https://example.com/"]
	assert result.candidates == ("https://example.com/page", "https://other.example.org/page")
	assert result.duplicate_urls == ("https://example.com/", "https://example.com/page")
	assert result.invalid_urls == ("javascript:void(0)",)


def test_invalid_start_and_discovery_failure_are_structured() -> None:
	invalid, invalid_policy, invalid_fetcher, _, _ = make_orchestrator(failures={"not-a-url"})
	invalid_result = invalid.crawl(FakeSource(), "not-a-url")
	assert invalid_result.error == "invalid_start_url"
	assert invalid_policy.calls == [] and invalid_fetcher.calls == []
	failing_discovery, _, _, _, _ = make_orchestrator(discovery_failure=True)
	assert failing_discovery.crawl(FakeSource(), "https://example.com/").error == "discovery_failed"


def test_orchestrator_fetches_only_the_start_document_and_empty_html_is_valid() -> None:
	orchestrator, _, fetcher, discoverer, _ = make_orchestrator(
		urls=tuple(f"https://example.com/{index}" for index in range(10)),
		fetch_result=make_fetch_result(content=b""),
	)
	result = orchestrator.crawl(FakeSource(), "https://example.com/")
	assert len(fetcher.calls) == 1
	assert len(discoverer.calls) == 1
	assert len(result.candidates) == 10