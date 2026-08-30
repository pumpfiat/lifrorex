from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from app.crawler.types import CrawlOutcome, PolicyOutcome, PolicyReason


@dataclass(frozen=True, slots=True)
class CrawlRequest:
	source_id: int
	start_urls: tuple[str, ...]
	max_depth: int = 0
	max_urls: int | None = None
	context: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FetchResponse:
	requested_url: str
	final_url: str
	status_code: int
	content_type: str | None = None
	content: bytes = b""


@dataclass(frozen=True, slots=True)
class PolicyDecision:
	allowed: bool
	outcome: PolicyOutcome
	reason: PolicyReason
	url: str
	source_id: int
	robots_url: str | None = None
	user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class CrawlResult:
	source_id: int
	requested_url: str
	outcome: CrawlOutcome
	succeeded: bool
	final_url: str | None = None
	http_status: int | None = None
	content_type: str | None = None
	response_size: int | None = None
	content: bytes = b""
	response_headers: Mapping[str, str] = field(default_factory=dict)
	error: str | None = None
	fetched_at: datetime | None = None
	started_at: datetime | None = None
	finished_at: datetime | None = None
	discovered_urls: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CrawlOperationResult:
	start_url: str
	canonical_url: str | None
	policy: PolicyDecision | None
	fetched: bool
	fetch_result: CrawlResult | None
	html_processed: bool
	candidates: tuple[str, ...] = ()
	duplicate_urls: tuple[str, ...] = ()
	invalid_urls: tuple[str, ...] = ()
	error: str | None = None


@dataclass(frozen=True, slots=True)
class RecursiveCrawlResult:
	start_url: str
	canonical_start_url: str | None
	max_pages: int
	page_results: tuple[CrawlOperationResult, ...]
	policy_denied_urls: tuple[str, ...]
	failed_urls: tuple[str, ...]
	invalid_urls: tuple[str, ...]
	duplicate_urls: tuple[str, ...]
	limit_reached: bool