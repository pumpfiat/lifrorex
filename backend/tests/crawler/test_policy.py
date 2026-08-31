from dataclasses import dataclass

import pytest

from app.crawler.policy import RobotsCrawlPolicy
from app.crawler.robots import RobotsResponse
from app.crawler.types import PolicyOutcome, PolicyReason


@dataclass
class PolicySource:
	id: int = 1
	url: str = "https://unit.test/source/path"
	active: bool = True
	crawl_allowed: bool = True


class FakeRobotsRetriever:
	def __init__(self, responses: dict[str, RobotsResponse]) -> None:
		self.responses = responses
		self.requested_urls: list[str] = []

	def retrieve(self, robots_url: str) -> RobotsResponse:
		self.requested_urls.append(robots_url)
		return self.responses[robots_url]


def make_policy(content: str, origin: str = "https://unit.test") -> tuple[RobotsCrawlPolicy, FakeRobotsRetriever]:
	robots_url = f"{origin}/robots.txt"
	retriever = FakeRobotsRetriever({robots_url: RobotsResponse(200, content.encode())})
	return RobotsCrawlPolicy(retriever), retriever


def test_inactive_source_is_denied_without_robots_request() -> None:
	policy, retriever = make_policy("User-agent: *\nAllow: /\n")
	decision = policy.evaluate(PolicySource(active=False), "https://unit.test/page")
	assert decision.reason is PolicyReason.SOURCE_INACTIVE
	assert decision.allowed is False
	assert retriever.requested_urls == []


def test_crawl_disabled_source_is_denied_without_robots_request() -> None:
	policy, retriever = make_policy("User-agent: *\nAllow: /\n")
	decision = policy.evaluate(PolicySource(crawl_allowed=False), "https://unit.test/page")
	assert decision.reason is PolicyReason.SOURCE_CRAWL_NOT_ALLOWED
	assert retriever.requested_urls == []


def test_robots_allow_and_disallow_rules() -> None:
	policy, _ = make_policy("User-agent: LiforexBot\nDisallow: /private/\nAllow: /private/public/\n")
	assert policy.evaluate(PolicySource(), "https://unit.test/private/page").reason is PolicyReason.ROBOTS_DISALLOWED
	assert policy.evaluate(PolicySource(), "https://unit.test/private/public/page").reason is PolicyReason.ROBOTS_ALLOWED


def test_other_user_agent_rules_do_not_apply_to_liforex() -> None:
	policy, _ = make_policy("User-agent: OtherBot\nDisallow: /\n")
	decision = policy.evaluate(PolicySource(), "https://unit.test/page")
	assert decision.outcome is PolicyOutcome.ALLOWED
	assert decision.reason is PolicyReason.ROBOTS_ALLOWED


def test_empty_robots_file_allows_crawling() -> None:
	policy, _ = make_policy("")
	decision = policy.evaluate(PolicySource(), "https://unit.test/page")
	assert decision.outcome is PolicyOutcome.ALLOWED
	assert decision.reason is PolicyReason.ROBOTS_ALLOWED


@pytest.mark.parametrize(
	("response", "outcome", "reason"),
	[
		(RobotsResponse(404), PolicyOutcome.ALLOWED, PolicyReason.ROBOTS_MISSING),
		(RobotsResponse(None, error="timeout"), PolicyOutcome.UNKNOWN, PolicyReason.ROBOTS_UNAVAILABLE),
		(RobotsResponse(503), PolicyOutcome.UNKNOWN, PolicyReason.ROBOTS_UNAVAILABLE),
		(RobotsResponse(200, b"\xff"), PolicyOutcome.UNKNOWN, PolicyReason.ROBOTS_INVALID),
		(RobotsResponse(200, b"not valid robots content"), PolicyOutcome.UNKNOWN, PolicyReason.ROBOTS_INVALID),
	],
)
def test_robots_failures_have_explicit_outcomes(
	response: RobotsResponse, outcome: PolicyOutcome, reason: PolicyReason
) -> None:
	retriever = FakeRobotsRetriever({"https://unit.test/robots.txt": response})
	decision = RobotsCrawlPolicy(retriever).evaluate(PolicySource(), "https://unit.test/page")
	assert decision.outcome is outcome
	assert decision.reason is reason


def test_http_to_https_redirect_on_same_host_is_not_cross_origin() -> None:
	# Regression test: a source registered as http://... whose site (like
	# almost all real .gov/.edu sites today) redirects everything to https
	# previously had every fetch rejected as CROSS_ORIGIN purely because the
	# scheme changed, even though it's genuinely the same site.
	policy, retriever = make_policy("User-agent: *\nAllow: /\n")
	decision = policy.evaluate(PolicySource(url="http://unit.test/source/path"), "https://unit.test/page")
	assert decision.outcome is PolicyOutcome.ALLOWED
	assert decision.reason is PolicyReason.ROBOTS_ALLOWED


def test_different_explicit_port_on_same_host_is_still_cross_origin() -> None:
	# A genuinely different port is a real signal of a different service,
	# not just a scheme upgrade -- this should NOT be treated as same-site.
	policy, retriever = make_policy("User-agent: *\nAllow: /\n")
	decision = policy.evaluate(
		PolicySource(url="http://unit.test:8080/source/path"), "https://unit.test/page"
	)
	assert decision.outcome is PolicyOutcome.DISALLOWED
	assert decision.reason is PolicyReason.CROSS_ORIGIN


@pytest.mark.parametrize(
	("url", "reason"),
	[
		("https://other.test/page", PolicyReason.CROSS_ORIGIN),
		("ftp://unit.test/file", PolicyReason.UNSUPPORTED_SCHEME),
		("/private/page", PolicyReason.INVALID_URL),
	],
)
def test_cross_origin_and_invalid_urls_are_denied_without_robots_fetch(
	url: str, reason: PolicyReason
) -> None:
	policy, retriever = make_policy("User-agent: *\nAllow: /\n")
	decision = policy.evaluate(PolicySource(), url)
	assert decision.outcome is PolicyOutcome.DISALLOWED
	assert decision.reason is reason
	assert retriever.requested_urls == []


def test_robots_cache_is_scoped_to_origin_and_never_fetches_target_url() -> None:
	retriever = FakeRobotsRetriever(
		{
			"https://unit.test/robots.txt": RobotsResponse(200, b"User-agent: *\nAllow: /\n"),
			"https://other.test/robots.txt": RobotsResponse(200, b"User-agent: *\nAllow: /\n"),
		}
	)
	policy = RobotsCrawlPolicy(retriever)
	policy.evaluate(PolicySource(), "https://unit.test/one")
	policy.evaluate(PolicySource(), "https://unit.test/two")
	policy.evaluate(PolicySource(url="https://other.test/"), "https://other.test/three")
	assert retriever.requested_urls == ["https://unit.test/robots.txt", "https://other.test/robots.txt"]