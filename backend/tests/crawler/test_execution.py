from dataclasses import dataclass

import pytest

from app.crawler.exceptions import PolicyError
from app.crawler.execution import BoundedCrawlExecutor
from app.crawler.models import CrawlResult, PolicyDecision
from app.crawler.orchestrator import SinglePageCrawlOrchestrator
from app.crawler.types import CrawlOutcome, PolicyOutcome, PolicyReason
from app.crawler.urls import HttpUrlNormalizer, InMemoryUrlDeduplicator


@dataclass
class Source:
	id: int = 1
	url: str = "https://example.com/"
	active: bool = True
	crawl_allowed: bool = True


class Policy:
	def __init__(self, denied: set[str] = set()) -> None:
		self.denied = denied
		self.calls: list[str] = []

	def evaluate(self, source: Source, url: str) -> PolicyDecision:
		self.calls.append(url)
		allowed = url not in self.denied
		return PolicyDecision(allowed, PolicyOutcome.ALLOWED if allowed else PolicyOutcome.DISALLOWED, PolicyReason.ROBOTS_ALLOWED if allowed else PolicyReason.ROBOTS_DISALLOWED, url, source.id)


class FailingPolicy(Policy):
	def __init__(self, failed_url: str) -> None:
		super().__init__()
		self.failed_url = failed_url

	def evaluate(self, source: Source, url: str) -> PolicyDecision:
		self.calls.append(url)
		if url == self.failed_url:
			raise PolicyError("unavailable")
		return super().evaluate(source, url)


class Fetcher:
	def __init__(self, pages: dict[str, CrawlResult]) -> None:
		self.pages = pages
		self.calls: list[str] = []

	def fetch(self, url: str) -> CrawlResult:
		self.calls.append(url)
		return self.pages[url]


class Discoverer:
	def __init__(self, links: dict[str, tuple[str, ...]]) -> None:
		self.links = links
		self.calls: list[str] = []

	def discover(self, content: bytes, base_url: str) -> tuple[str, ...]:
		self.calls.append(base_url)
		return self.links.get(base_url, ())


def response(url: str, content_type: str = "text/html", succeeded: bool = True) -> CrawlResult:
	return CrawlResult(1, url, CrawlOutcome.SUCCESS if succeeded else CrawlOutcome.CONNECTION_ERROR, succeeded, final_url=url, http_status=200 if succeeded else None, content_type=content_type, content=b"html", error=None if succeeded else "connection_error")


def make_executor(graph: dict[str, tuple[str, ...]], max_pages: int, denied: set[str] = set(), failures: set[str] = set(), pdfs: set[str] = set()) -> tuple[BoundedCrawlExecutor, Fetcher, Policy, Discoverer]:
	urls = {"https://example.com/"} | set(graph) | {url for links in graph.values() for url in links if url.startswith("http")}
	pages = {url: response(url, "application/pdf" if url in pdfs else "text/html", url not in failures) for url in urls}
	policy = Policy(denied)
	fetcher = Fetcher(pages)
	discoverer = Discoverer(graph)
	page = SinglePageCrawlOrchestrator(HttpUrlNormalizer(), InMemoryUrlDeduplicator(), policy, fetcher, discoverer)
	return BoundedCrawlExecutor(page, max_pages), fetcher, policy, discoverer


def test_page_limit_and_breadth_first_order() -> None:
	graph = {"https://example.com/": ("https://example.com/b", "https://example.com/c"), "https://example.com/b": ("https://example.com/d",), "https://example.com/c": ("https://example.com/e",), "https://example.com/d": (), "https://example.com/e": ()}
	executor, fetcher, _, _ = make_executor(graph, max_pages=5)
	result = executor.crawl(Source(), "https://example.com/")
	assert fetcher.calls == ["https://example.com/", "https://example.com/b", "https://example.com/c", "https://example.com/d", "https://example.com/e"]
	assert result.limit_reached is False
	limited, limited_fetcher, _, _ = make_executor(graph, max_pages=2)
	assert limited.crawl(Source(), "https://example.com/").limit_reached is True
	assert limited_fetcher.calls == ["https://example.com/", "https://example.com/b"]


def test_cycles_duplicates_and_self_links_fetch_each_page_once() -> None:
	graph = {"https://example.com/": ("https://example.com/", "https://example.com/b", "https://EXAMPLE.COM/b#top", "https://example.com/b"), "https://example.com/b": ("https://example.com/c",), "https://example.com/c": ("https://example.com/",)}
	executor, fetcher, _, _ = make_executor(graph, max_pages=10)
	result = executor.crawl(Source(), "https://example.com/")
	assert fetcher.calls == ["https://example.com/", "https://example.com/b", "https://example.com/c"]
	assert result.duplicate_urls == ("https://example.com/", "https://example.com/b", "https://example.com/b", "https://example.com/")


def test_policy_denial_fetch_failure_non_html_and_invalid_links_are_isolated() -> None:
	graph = {"https://example.com/": ("https://example.com/denied", "https://example.com/failure", "https://example.com/pdf", "javascript:void(0)", "https://example.com/good"), "https://example.com/good": ()}
	executor, fetcher, policy, discoverer = make_executor(graph, 10, {"https://example.com/denied"}, {"https://example.com/failure"}, {"https://example.com/pdf"})
	result = executor.crawl(Source(), "https://example.com/")
	assert fetcher.calls == ["https://example.com/", "https://example.com/failure", "https://example.com/pdf", "https://example.com/good"]
	assert policy.calls == ["https://example.com/", "https://example.com/denied", "https://example.com/failure", "https://example.com/pdf", "https://example.com/good"]
	assert result.policy_denied_urls == ("https://example.com/denied",)
	assert result.failed_urls == ("https://example.com/failure",)
	assert result.invalid_urls == ("javascript:void(0)",)
	assert discoverer.calls == ["https://example.com/", "https://example.com/good"]


def test_long_chain_uses_queue_and_invalid_start_does_not_fetch() -> None:
	chain = {f"https://example.com/{index}": (f"https://example.com/{index + 1}",) for index in range(100)}
	chain["https://example.com/"] = ("https://example.com/0",)
	executor, fetcher, _, _ = make_executor(chain, max_pages=50)
	assert len(executor.crawl(Source(), "https://example.com/").page_results) == 50
	assert len(fetcher.calls) == 50
	invalid, invalid_fetcher, _, _ = make_executor({}, 2)
	result = invalid.crawl(Source(), "not-a-url")
	assert result.page_results[0].error == "invalid_start_url"
	assert invalid_fetcher.calls == []


def test_policy_failure_prevents_fetch_and_does_not_abort_queued_pages() -> None:
	graph = {"https://example.com/": ("https://example.com/policy-error", "https://example.com/good"), "https://example.com/good": ()}
	executor, fetcher, _, _ = make_executor(graph, 10)
	executor.page_orchestrator.crawl_policy = FailingPolicy("https://example.com/policy-error")
	result = executor.crawl(Source(), "https://example.com/")
	assert fetcher.calls == ["https://example.com/", "https://example.com/good"]
	assert result.page_results[1].error == "policy_failed"
	assert result.page_results[2].canonical_url == "https://example.com/good"


def test_max_pages_must_be_positive() -> None:
	executor, _, _, _ = make_executor({}, 1)
	with pytest.raises(ValueError, match="max_pages must be positive"):
		BoundedCrawlExecutor(executor.page_orchestrator, max_pages=0)