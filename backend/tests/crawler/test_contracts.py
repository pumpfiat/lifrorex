import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from app.crawler.exceptions import CrawlerError, DiscoveryError, FetchError, PolicyError
from app.crawler.interfaces import CrawlOrchestrator, CrawlPolicy, Fetcher, UrlDiscoverer
from app.crawler.models import CrawlRequest, CrawlResult
from app.crawler.types import CrawlOutcome


BACKEND_DIR = Path(__file__).resolve().parents[2]


def test_crawler_package_imports_without_side_effects() -> None:
	result = subprocess.run(
		[
			sys.executable,
			"-c",
			"import app.crawler; import app.crawler.models; import app.crawler.types; "
			"import app.crawler.interfaces; import app.crawler.exceptions",
		],
		cwd=BACKEND_DIR,
		capture_output=True,
		text=True,
		check=False,
	)

	assert result.returncode == 0, result.stderr


def test_crawl_outcomes_include_expected_states() -> None:
	assert set(CrawlOutcome) == {
		CrawlOutcome.SUCCESS,
		CrawlOutcome.BLOCKED,
		CrawlOutcome.DISALLOWED,
		CrawlOutcome.NOT_FOUND,
		CrawlOutcome.CLIENT_ERROR,
		CrawlOutcome.SERVER_ERROR,
		CrawlOutcome.TIMEOUT,
		CrawlOutcome.CONNECTION_ERROR,
		CrawlOutcome.INVALID_RESPONSE,
		CrawlOutcome.UNKNOWN_ERROR,
	}


def test_crawl_request_is_database_independent() -> None:
	request = CrawlRequest(
		source_id=1,
		start_urls=("https://example.test/",),
		max_depth=2,
		max_urls=10,
		context={"initiator": "test"},
	)

	assert request.source_id == 1
	assert request.start_urls == ("https://example.test/",)
	assert request.context == {"initiator": "test"}


def test_crawl_result_is_database_independent() -> None:
	now = datetime.now(timezone.utc)
	result = CrawlResult(
		source_id=1,
		requested_url="https://example.test/",
		final_url="https://example.test/final",
		http_status=200,
		succeeded=True,
		content_type="text/html",
		response_size=128,
		outcome=CrawlOutcome.SUCCESS,
		started_at=now,
		finished_at=now,
		discovered_urls=("https://example.test/next",),
	)

	assert result.outcome is CrawlOutcome.SUCCESS
	assert result.discovered_urls == ("https://example.test/next",)


def test_exceptions_and_interfaces_are_available() -> None:
	assert issubclass(FetchError, CrawlerError)
	assert issubclass(PolicyError, CrawlerError)
	assert issubclass(DiscoveryError, CrawlerError)
	assert Fetcher.__name__ == "Fetcher"
	assert CrawlPolicy.__name__ == "CrawlPolicy"
	assert UrlDiscoverer.__name__ == "UrlDiscoverer"
	assert CrawlOrchestrator.__name__ == "CrawlOrchestrator"