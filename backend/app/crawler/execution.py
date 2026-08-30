from collections import deque

from app.crawler.interfaces import CrawlSource
from app.crawler.models import CrawlOperationResult, RecursiveCrawlResult
from app.crawler.orchestrator import SinglePageCrawlOrchestrator


class BoundedCrawlExecutor:
	DEFAULT_MAX_PAGES = 10

	def __init__(self, page_orchestrator: SinglePageCrawlOrchestrator, max_pages: int = DEFAULT_MAX_PAGES) -> None:
		if max_pages <= 0:
			raise ValueError("max_pages must be positive")
		self.page_orchestrator = page_orchestrator
		self.max_pages = max_pages

	def crawl(self, source: CrawlSource, start_url: str) -> RecursiveCrawlResult:
		first_result = self.page_orchestrator.crawl(source, start_url)
		if first_result.canonical_url is None:
			return RecursiveCrawlResult(
				start_url, None, self.max_pages, (first_result,), (), (), (), (), False
			)

		pages = [first_result]
		queue = deque(first_result.candidates)
		fetched_pages = int(first_result.fetched)
		while queue and fetched_pages < self.max_pages:
			url = queue.popleft()
			page = self.page_orchestrator.crawl(source, url, register_start=False)
			pages.append(page)
			fetched_pages += int(page.fetched)
			queue.extend(page.candidates)

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