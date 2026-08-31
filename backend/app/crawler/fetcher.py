import time
from collections.abc import Iterator
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

from app.crawler.models import CrawlResult
from app.crawler.types import CRAWLER_USER_AGENT, CrawlOutcome


class HttpFetcher:
	DEFAULT_TIMEOUT_SECONDS = 10.0
	DEFAULT_MAX_RESPONSE_SIZE = 10 * 1024 * 1024
	# Retries and rate-limiting default to OFF (0). Previously there was no
	# retry/backoff and no throttling at all -- a single transient timeout
	# gave up permanently, and nothing stopped hammering a host with rapid
	# sequential requests. The capability is added here, but defaults are
	# conservative so existing callers (and existing tests, several of which
	# call fetch() once and expect exactly one result with no delay) see no
	# behavior change unless a caller explicitly opts in with a positive
	# max_retries / min_request_interval_seconds. Whoever wires up the real
	# crawl process should pass explicit non-zero values -- e.g. max_retries=2,
	# min_request_interval_seconds=1.0 -- to actually get the benefit.
	DEFAULT_MAX_RETRIES = 0
	DEFAULT_BACKOFF_BASE_SECONDS = 1.0
	DEFAULT_MIN_REQUEST_INTERVAL_SECONDS = 0.0
	USER_AGENT = CRAWLER_USER_AGENT

	# 429/503 are classic "try again shortly" signals; other 5xx are often
	# transient too. 4xx other than 429 (e.g. 403, 404) are deliberately not
	# retried -- retrying won't fix a genuine client-side error or block.
	RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

	def __init__(
		self,
		source_id: int,
		timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
		max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE,
		max_retries: int = DEFAULT_MAX_RETRIES,
		backoff_base_seconds: float = DEFAULT_BACKOFF_BASE_SECONDS,
		min_request_interval_seconds: float = DEFAULT_MIN_REQUEST_INTERVAL_SECONDS,
		transport: httpx.BaseTransport | None = None,
		sleep_fn=time.sleep,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		if max_response_size <= 0:
			raise ValueError("max_response_size must be positive")
		if max_retries < 0:
			raise ValueError("max_retries must be non-negative")
		if backoff_base_seconds < 0:
			raise ValueError("backoff_base_seconds must be non-negative")
		if min_request_interval_seconds < 0:
			raise ValueError("min_request_interval_seconds must be non-negative")

		self.source_id = source_id
		self.timeout_seconds = timeout_seconds
		self.max_response_size = max_response_size
		self.max_retries = max_retries
		self.backoff_base_seconds = backoff_base_seconds
		self.min_request_interval_seconds = min_request_interval_seconds
		self.transport = transport
		self._sleep = sleep_fn
		# Per-host last-request timestamp, for the rate-limit throttle below.
		# Lives for the lifetime of this fetcher instance -- typically one
		# crawl run reuses a single fetcher across many fetch() calls.
		self._last_request_at: dict[str, float] = {}

	def fetch(self, url: str) -> CrawlResult:
		started_at = datetime.now(timezone.utc)
		result: CrawlResult
		for attempt in range(self.max_retries + 1):
			self._respect_rate_limit(url)
			result = self._fetch_once(url, started_at)
			if result.succeeded or not self._is_retryable(result):
				return result
			if attempt < self.max_retries:
				delay = self.backoff_base_seconds * (2 ** attempt)
				retry_after = self._retry_after_seconds(result)
				if retry_after is not None:
					delay = max(delay, retry_after)
				self._sleep(delay)
		return result

	def _is_retryable(self, result: CrawlResult) -> bool:
		if result.outcome in (CrawlOutcome.TIMEOUT, CrawlOutcome.CONNECTION_ERROR):
			return True
		return result.http_status is not None and result.http_status in self.RETRYABLE_STATUS_CODES

	@staticmethod
	def _retry_after_seconds(result: CrawlResult) -> float | None:
		value = result.response_headers.get("retry-after") if result.response_headers else None
		if value is None:
			return None
		try:
			return float(value)
		except ValueError:
			return None

	def _respect_rate_limit(self, url: str) -> None:
		if self.min_request_interval_seconds <= 0:
			return
		host = urlsplit(url).hostname
		if host is None:
			return
		now = time.monotonic()
		last = self._last_request_at.get(host)
		if last is not None:
			wait = self.min_request_interval_seconds - (now - last)
			if wait > 0:
				self._sleep(wait)
		self._last_request_at[host] = time.monotonic()

	def _fetch_once(self, url: str, started_at: datetime) -> CrawlResult:
		try:
			with httpx.Client(
				timeout=self.timeout_seconds,
				follow_redirects=True,
				headers={"User-Agent": self.USER_AGENT},
				transport=self.transport,
			) as client:
				with client.stream("GET", url) as response:
					content_length = self._content_length(response)
					if content_length is not None and content_length > self.max_response_size:
						return self._response_too_large_result(
							url, response, started_at, content_length
						)

					content = self._read_content(response.iter_bytes())
					if content is None:
						return self._response_too_large_result(
							url, response, started_at, None
						)

					finished_at = datetime.now(timezone.utc)
					return CrawlResult(
						source_id=self.source_id,
						requested_url=url,
						final_url=str(response.url),
						http_status=response.status_code,
						content_type=response.headers.get("content-type"),
						response_size=len(content),
						content=content,
						response_headers=dict(response.headers),
						outcome=self._outcome_for_status(response.status_code),
						succeeded=200 <= response.status_code < 300,
						error=self._error_for_status(response.status_code),
						fetched_at=finished_at,
						started_at=started_at,
						finished_at=finished_at,
					)
		except httpx.TimeoutException:
			return self._network_failure_result(url, started_at, CrawlOutcome.TIMEOUT, "timeout")
		except httpx.RequestError:
			return self._network_failure_result(
				url, started_at, CrawlOutcome.CONNECTION_ERROR, "connection_error"
			)

	def _read_content(self, chunks: Iterator[bytes]) -> bytes | None:
		content = bytearray()
		for chunk in chunks:
			if len(content) + len(chunk) > self.max_response_size:
				return None
			content.extend(chunk)
		return bytes(content)

	def _content_length(self, response: httpx.Response) -> int | None:
		value = response.headers.get("content-length")
		if value is None:
			return None
		try:
			return int(value)
		except ValueError:
			return None

	def _response_too_large_result(
		self,
		requested_url: str,
		response: httpx.Response,
		started_at: datetime,
		response_size: int | None,
	) -> CrawlResult:
		finished_at = datetime.now(timezone.utc)
		return CrawlResult(
			source_id=self.source_id,
			requested_url=requested_url,
			final_url=str(response.url),
			http_status=response.status_code,
			content_type=response.headers.get("content-type"),
			response_size=response_size,
			response_headers=dict(response.headers),
			outcome=CrawlOutcome.INVALID_RESPONSE,
			succeeded=False,
			error="response_too_large",
			fetched_at=finished_at,
			started_at=started_at,
			finished_at=finished_at,
		)

	def _network_failure_result(
		self,
		url: str,
		started_at: datetime,
		outcome: CrawlOutcome,
		error: str,
	) -> CrawlResult:
		finished_at = datetime.now(timezone.utc)
		return CrawlResult(
			source_id=self.source_id,
			requested_url=url,
			outcome=outcome,
			succeeded=False,
			error=error,
			fetched_at=finished_at,
			started_at=started_at,
			finished_at=finished_at,
		)

	@staticmethod
	def _outcome_for_status(status_code: int) -> CrawlOutcome:
		if 200 <= status_code < 300:
			return CrawlOutcome.SUCCESS
		if status_code in {403, 429}:
			return CrawlOutcome.BLOCKED
		if status_code == 404:
			return CrawlOutcome.NOT_FOUND
		if 400 <= status_code < 500:
			return CrawlOutcome.CLIENT_ERROR
		if 500 <= status_code < 600:
			return CrawlOutcome.SERVER_ERROR
		return CrawlOutcome.INVALID_RESPONSE

	@staticmethod
	def _error_for_status(status_code: int) -> str | None:
		return None if 200 <= status_code < 300 else f"http_{status_code}"