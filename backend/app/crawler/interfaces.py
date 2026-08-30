from typing import Protocol

from app.crawler.models import CrawlRequest, CrawlResult, PolicyDecision


class Fetcher(Protocol):
	def fetch(self, url: str) -> CrawlResult: ...


class CrawlPolicy(Protocol):
	def evaluate(self, source: "CrawlSource", url: str) -> PolicyDecision: ...


class CrawlSource(Protocol):
	id: int
	url: str
	active: bool
	crawl_allowed: bool


class RobotsRetriever(Protocol):
	def retrieve(self, robots_url: str) -> "RobotsResponse": ...


class UrlDiscoverer(Protocol):
	def discover(self, content: bytes, base_url: str) -> tuple[str, ...]: ...


class CrawlOrchestrator(Protocol):
	def crawl(self, request: CrawlRequest) -> tuple[CrawlResult, ...]: ...