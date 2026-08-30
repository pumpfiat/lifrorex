from app.crawler.exceptions import DiscoveryError, PolicyError, UrlNormalizationError
from app.crawler.interfaces import CrawlPolicy, CrawlSource, Fetcher, UrlDeduplicator, UrlDiscoverer, UrlNormalizer
from app.crawler.models import CrawlOperationResult


class SinglePageCrawlOrchestrator:
	def __init__(
		self,
		url_normalizer: UrlNormalizer,
		deduplicator: UrlDeduplicator,
		crawl_policy: CrawlPolicy,
		fetcher: Fetcher,
		link_discoverer: UrlDiscoverer,
	) -> None:
		self.url_normalizer = url_normalizer
		self.deduplicator = deduplicator
		self.crawl_policy = crawl_policy
		self.fetcher = fetcher
		self.link_discoverer = link_discoverer

	def crawl(
		self, source: CrawlSource, start_url: str, register_start: bool = True
	) -> CrawlOperationResult:
		try:
			start = self.url_normalizer.normalize(start_url)
		except UrlNormalizationError:
			return CrawlOperationResult(start_url, None, None, False, None, False, error="invalid_start_url")

		if register_start and not self.deduplicator.check_and_mark(start):
			return CrawlOperationResult(
				start_url, start.canonical, None, False, None, False, error="start_url_duplicate"
			)

		try:
			policy = self.crawl_policy.evaluate(source, start.canonical)
		except PolicyError:
			return CrawlOperationResult(
				start_url, start.canonical, None, False, None, False, error="policy_failed"
			)
		if not policy.allowed:
			return CrawlOperationResult(start_url, start.canonical, policy, False, None, False)

		fetch_result = self.fetcher.fetch(start.canonical)
		if not fetch_result.succeeded:
			return CrawlOperationResult(
				start_url, start.canonical, policy, True, fetch_result, False, error=fetch_result.error
			)
		if not self._is_html(fetch_result.content_type):
			return CrawlOperationResult(start_url, start.canonical, policy, True, fetch_result, False)

		try:
			discovered = self.link_discoverer.discover(
				fetch_result.content, fetch_result.final_url or start.canonical
			)
		except DiscoveryError:
			return CrawlOperationResult(
				start_url, start.canonical, policy, True, fetch_result, False, error="discovery_failed"
			)

		candidates: list[str] = []
		duplicates: list[str] = []
		invalid: list[str] = []
		for url in discovered:
			try:
				normalized = self.url_normalizer.normalize(url)
			except UrlNormalizationError:
				invalid.append(url)
				continue
			if self.deduplicator.check_and_mark(normalized):
				candidates.append(normalized.canonical)
			else:
				duplicates.append(normalized.canonical)

		return CrawlOperationResult(
			start_url,
			start.canonical,
			policy,
			True,
			fetch_result,
			True,
			tuple(candidates),
			tuple(duplicates),
			tuple(invalid),
		)

	@staticmethod
	def _is_html(content_type: str | None) -> bool:
		return content_type is not None and content_type.split(";", maxsplit=1)[0].strip().casefold() == "text/html"