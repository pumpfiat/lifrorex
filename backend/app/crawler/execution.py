from collections import deque

from app.crawler.interfaces import CrawlSource
from app.crawler.models import CrawlOperationResult, RecursiveCrawlResult
from app.crawler.orchestrator import SinglePageCrawlOrchestrator


class BoundedCrawlExecutor:
	DEFAULT_MAX_PAGES = 10

	def __init__(
		self,
		page_orchestrator: SinglePageCrawlOrchestrator,
		max_pages: int = DEFAULT_MAX_PAGES,
		max_depth: int | None = None,
	) -> None:
		if max_pages <= 0:
			raise ValueError("max_pages must be positive")
		if max_depth is not None and max_depth < 0:
			raise ValueError("max_depth must be non-negative")
		self.page_orchestrator = page_orchestrator
		self.max_pages = max_pages
		# Defaults to unlimited (None) -- same as the previous, unbounded
		# behavior -- so nothing changes for existing callers unless this is
		# explicitly set. Previously there was no depth tracking at all: a
		# crawl bounded only by max_pages could wander arbitrarily far from
		# the seed URL (many hops away) before exhausting its page budget,
		# rather than staying close to the actually-relevant seed content.
		self.max_depth = max_depth

	def crawl(self, source: CrawlSource, start_url: str) -> RecursiveCrawlResult:
		first_result = self.page_orchestrator.crawl(source, start_url)
		if first_result.canonical_url is None:
			return RecursiveCrawlResult(
				start_url, None, self.max_pages, (first_result,), (), (), (), (), False
			)

		pages = [first_result]
		# (url, depth) pairs -- the start URL is depth 0, its discovered
		# links are depth 1, their links depth 2, and so on.
		queue: deque[tuple[str, int]] = deque((url, 1) for url in first_result.candidates)
		fetched_pages = int(first_result.fetched)
		while queue and fetched_pages < self.max_pages:
			url, depth = queue.popleft()
			if self.max_depth is not None and depth > self.max_depth:
				continue
			page = self.page_orchestrator.crawl(source, url, register_start=False)
			pages.append(page)
			fetched_pages += int(page.fetched)
			if self.max_depth is None or depth < self.max_depth:
				queue.extend((candidate, depth + 1) for candidate in page.candidates)

		return RecursiveCrawlResult(
			start_url=start_url,
			canonical_start_url=first_result.canonical_url,
			max_pages=self.max_pages,
			page_results=tuple(pages),
			policy_denied_urls=tuple(
				page.canonical_url for page in pages if page.policy is not None and not page.policy.allowed and page.canonical_url is not None
			),
			failed_urls=tuple(
				page.canonical_url for page in pages if page.fetched and page.fetch_result is not None and not page.fetch_result.succeeded and page.canonical_url is not None
			),
			invalid_urls=tuple(url for page in pages for url in page.invalid_urls),
			duplicate_urls=tuple(url for page in pages for url in page.duplicate_urls),
			limit_reached=bool(queue) and fetched_pages >= self.max_pages,
		)