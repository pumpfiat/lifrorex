from collections.abc import Iterator
from datetime import datetime, timezone

import httpx

from app.crawler.models import CrawlResult
from app.crawler.types import CRAWLER_USER_AGENT, CrawlOutcome


class HttpFetcher:
	DEFAULT_TIMEOUT_SECONDS = 10.0
	DEFAULT_MAX_RESPONSE_SIZE = 10 * 1024 * 1024
	USER_AGENT = CRAWLER_USER_AGENT

	def __init__(
		self,
		source_id: int,
		timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
		max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE,
		transport: httpx.BaseTransport | None = None,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		if max_response_size <= 0:
			raise ValueError("max_response_size must be positive")

		self.source_id = source_id
		self.timeout_seconds = timeout_seconds
		self.max_response_size = max_response_size
		self.transport = transport

	def fetch(self, url: str) -> CrawlResult:
		started_at = datetime.now(timezone.utc)
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