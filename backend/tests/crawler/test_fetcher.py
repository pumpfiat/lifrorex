import httpx
import pytest

from app.crawler.fetcher import HttpFetcher
from app.crawler.types import CrawlOutcome


def make_fetcher(handler: httpx.MockTransport.Handler, **kwargs: object) -> HttpFetcher:
	return HttpFetcher(source_id=1, transport=httpx.MockTransport(handler), **kwargs)


def test_fetch_returns_raw_success_response_and_user_agent() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		assert request.headers["user-agent"] == "LiforexBot/0.1"
		return httpx.Response(
			200,
			headers={"content-type": "text/html", "x-request-id": "request-1"},
			content=b"<html>hello</html>",
			request=request,
		)

	result = make_fetcher(handler).fetch("https://unit.test/start")

	assert result.succeeded is True
	assert result.outcome is CrawlOutcome.SUCCESS
	assert result.requested_url == "https://unit.test/start"
	assert result.final_url == "https://unit.test/start"
	assert result.http_status == 200
	assert result.content_type == "text/html"
	assert result.content == b"<html>hello</html>"
	assert result.response_size == len(result.content)
	assert result.response_headers["x-request-id"] == "request-1"
	assert result.error is None
	assert result.fetched_at is not None


def test_fetch_follows_redirects_and_records_final_url() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		if request.url.path == "/start":
			return httpx.Response(302, headers={"location": "/final"}, request=request)
		return httpx.Response(200, content=b"done", request=request)

	result = make_fetcher(handler).fetch("https://unit.test/start")

	assert result.succeeded is True
	assert result.requested_url == "https://unit.test/start"
	assert result.final_url == "https://unit.test/final"
	assert result.content == b"done"


@pytest.mark.parametrize(
	("status_code", "outcome"),
	[
		(404, CrawlOutcome.NOT_FOUND),
		(403, CrawlOutcome.BLOCKED),
		(429, CrawlOutcome.BLOCKED),
		(500, CrawlOutcome.SERVER_ERROR),
	],
)
def test_fetch_returns_structured_http_failure(
	status_code: int, outcome: CrawlOutcome
) -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(status_code, content=b"failure", request=request)

	result = make_fetcher(handler).fetch("https://unit.test/failure")

	assert result.succeeded is False
	assert result.outcome is outcome
	assert result.http_status == status_code
	assert result.error == f"http_{status_code}"
	assert result.content == b"failure"


def test_fetch_converts_timeout_to_structured_failure() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ReadTimeout("timed out", request=request)

	result = make_fetcher(handler).fetch("https://unit.test/timeout")

	assert result.succeeded is False
	assert result.outcome is CrawlOutcome.TIMEOUT
	assert result.http_status is None
	assert result.error == "timeout"


def test_fetch_converts_connection_failure_to_structured_failure() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		raise httpx.ConnectError("connection failed", request=request)

	result = make_fetcher(handler).fetch("https://unit.test/connection")

	assert result.succeeded is False
	assert result.outcome is CrawlOutcome.CONNECTION_ERROR
	assert result.http_status is None
	assert result.error == "connection_error"


@pytest.mark.parametrize("content_type", ["text/html", "application/pdf", "application/json"])
def test_fetch_captures_content_type(content_type: str) -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(200, headers={"content-type": content_type}, content=b"raw", request=request)

	result = make_fetcher(handler).fetch("https://unit.test/content")

	assert result.content_type == content_type


def test_fetch_rejects_oversized_response_before_reading_content() -> None:
	def handler(request: httpx.Request) -> httpx.Response:
		return httpx.Response(
			200,
			headers={"content-length": "11", "content-type": "text/plain"},
			content=b"not-read-body",
			request=request,
		)

	result = make_fetcher(handler, max_response_size=10).fetch("https://unit.test/large")

	assert result.succeeded is False
	assert result.outcome is CrawlOutcome.INVALID_RESPONSE
	assert result.error == "response_too_large"
	assert result.content == b""
	assert result.response_size == 11


@pytest.mark.parametrize(
	("constructor_arguments", "message"),
	[
		({"timeout_seconds": 0}, "timeout_seconds must be positive"),
		({"max_response_size": 0}, "max_response_size must be positive"),
	],
)
def test_fetcher_rejects_invalid_limits(
	constructor_arguments: dict[str, int], message: str
) -> None:
	with pytest.raises(ValueError, match=message):
		HttpFetcher(source_id=1, **constructor_arguments)