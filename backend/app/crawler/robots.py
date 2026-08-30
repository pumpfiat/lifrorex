from dataclasses import dataclass

import httpx

from app.crawler.types import CRAWLER_USER_AGENT


@dataclass(frozen=True, slots=True)
class RobotsResponse:
	status_code: int | None
	content: bytes = b""
	error: str | None = None


class HttpRobotsRetriever:
	DEFAULT_TIMEOUT_SECONDS = 10.0
	DEFAULT_MAX_RESPONSE_SIZE = 512 * 1024

	def __init__(
		self,
		timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
		max_response_size: int = DEFAULT_MAX_RESPONSE_SIZE,
		transport: httpx.BaseTransport | None = None,
	) -> None:
		if timeout_seconds <= 0:
			raise ValueError("timeout_seconds must be positive")
		if max_response_size <= 0:
			raise ValueError("max_response_size must be positive")
		self.timeout_seconds = timeout_seconds
		self.max_response_size = max_response_size
		self.transport = transport

	def retrieve(self, robots_url: str) -> RobotsResponse:
		try:
			with httpx.Client(
				timeout=self.timeout_seconds,
				follow_redirects=True,
				headers={"User-Agent": CRAWLER_USER_AGENT},
				transport=self.transport,
			) as client:
				with client.stream("GET", robots_url) as response:
					content_length = response.headers.get("content-length")
					if content_length is not None and int(content_length) > self.max_response_size:
						return RobotsResponse(response.status_code, error="response_too_large")
					content = bytearray()
					for chunk in response.iter_bytes():
						if len(content) + len(chunk) > self.max_response_size:
							return RobotsResponse(response.status_code, error="response_too_large")
						content.extend(chunk)
					return RobotsResponse(response.status_code, bytes(content))
		except (httpx.RequestError, ValueError):
			return RobotsResponse(None, error="retrieval_failed")