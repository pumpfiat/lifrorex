from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urlsplit

from app.crawler.interfaces import CrawlSource, RobotsRetriever
from app.crawler.models import PolicyDecision
from app.crawler.robots import RobotsResponse
from app.crawler.types import CRAWLER_USER_AGENT, PolicyOutcome, PolicyReason


@dataclass(frozen=True, slots=True)
class _CachedRobots:
	parser: robotparser.RobotFileParser | None
	reason: PolicyReason


class RobotsCrawlPolicy:
	def __init__(self, robots_retriever: RobotsRetriever) -> None:
		self.robots_retriever = robots_retriever
		self._cache: dict[str, _CachedRobots] = {}

	def evaluate(self, source: CrawlSource, url: str) -> PolicyDecision:
		if not source.active:
			return self._decision(source.id, url, PolicyOutcome.DISALLOWED, PolicyReason.SOURCE_INACTIVE)
		if not source.crawl_allowed:
			return self._decision(source.id, url, PolicyOutcome.DISALLOWED, PolicyReason.SOURCE_CRAWL_NOT_ALLOWED)

		# "Same site" comparison deliberately ignores scheme (see _site()
		# below) -- a source registered as http://example.gov whose site
		# redirects everything to https://example.gov (the default behavior
		# of most real government/education sites today) would previously
		# have every single fetch rejected as CROSS_ORIGIN, since scheme was
		# part of the exact-match comparison. Subdomain crossing (e.g.
		# docs.example.gov vs www.example.gov) is still intentionally
		# disallowed -- that's a bigger, separate decision (would need
		# accurate registrable-domain matching to do safely) rather than a
		# straightforward bug fix.
		source_site = self._site(source.url)
		target_site = self._site(url)
		if target_site is None:
			reason = PolicyReason.UNSUPPORTED_SCHEME if urlsplit(url).scheme else PolicyReason.INVALID_URL
			return self._decision(source.id, url, PolicyOutcome.DISALLOWED, reason)
		if source_site is None or source_site != target_site:
			return self._decision(source.id, url, PolicyOutcome.DISALLOWED, PolicyReason.CROSS_ORIGIN)

		# robots.txt must still be fetched using the TARGET url's actual
		# scheme (not the source's original scheme) -- some sites no longer
		# serve plain http at all, so this has to reflect where the URL
		# actually resolved, not where the source was originally registered.
		target_origin = self._origin(url)

		robots_url = f"{target_origin}/robots.txt"
		cached = self._cache.get(target_origin)
		if cached is None:
			cached = self._retrieve_robots(robots_url)
			self._cache[target_origin] = cached

		if cached.parser is None:
			outcome = PolicyOutcome.ALLOWED if cached.reason is PolicyReason.ROBOTS_MISSING else PolicyOutcome.UNKNOWN
			return self._decision(source.id, url, outcome, cached.reason, robots_url)

		if cached.parser.can_fetch(CRAWLER_USER_AGENT, url):
			return self._decision(source.id, url, PolicyOutcome.ALLOWED, PolicyReason.ROBOTS_ALLOWED, robots_url)
		return self._decision(source.id, url, PolicyOutcome.DISALLOWED, PolicyReason.ROBOTS_DISALLOWED, robots_url)

	def _retrieve_robots(self, robots_url: str) -> _CachedRobots:
		response: RobotsResponse = self.robots_retriever.retrieve(robots_url)
		if response.status_code == 404:
			return _CachedRobots(None, PolicyReason.ROBOTS_MISSING)
		if response.status_code != 200 or response.error is not None:
			return _CachedRobots(None, PolicyReason.ROBOTS_UNAVAILABLE)
		try:
			lines = response.content.decode("utf-8").splitlines()
		except UnicodeDecodeError:
			return _CachedRobots(None, PolicyReason.ROBOTS_INVALID)
		if lines and not self._has_robots_directive(lines):
			return _CachedRobots(None, PolicyReason.ROBOTS_INVALID)

		parser = robotparser.RobotFileParser(robots_url)
		parser.parse(lines)
		return _CachedRobots(parser, PolicyReason.ROBOTS_ALLOWED)

	@staticmethod
	def _has_robots_directive(lines: list[str]) -> bool:
		return any(
			line.split(":", maxsplit=1)[0].strip().casefold()
			in {"user-agent", "allow", "disallow"}
			for line in lines
			if line.strip() and not line.lstrip().startswith("#") and ":" in line
		)

	@staticmethod
	def _origin(url: str) -> str | None:
		parsed = urlsplit(url)
		if parsed.scheme not in {"http", "https"} or not parsed.netloc:
			return None
		return f"{parsed.scheme}://{parsed.netloc}"

	@staticmethod
	def _site(url: str) -> tuple[str, int | None] | None:
		"""(hostname, port) used for same-site comparison, deliberately
		ignoring scheme. Each URL's own default port (80 for http, 443 for
		https) normalizes to None, so http://x and https://x -- with no
		explicit non-default port on either side -- compare equal. An
		explicit non-default port (e.g. http://x:8080) is preserved and will
		correctly NOT match a plain https://x, since that's a real signal of
		a different service, not just a scheme upgrade."""
		parsed = urlsplit(url)
		if parsed.scheme not in {"http", "https"} or not parsed.netloc:
			return None
		hostname = parsed.hostname
		if hostname is None:
			return None
		port = parsed.port
		if port == 80 and parsed.scheme == "http":
			port = None
		if port == 443 and parsed.scheme == "https":
			port = None
		return (hostname.lower(), port)

	@staticmethod
	def _decision(
		source_id: int,
		url: str,
		outcome: PolicyOutcome,
		reason: PolicyReason,
		robots_url: str | None = None,
	) -> PolicyDecision:
		return PolicyDecision(
			allowed=outcome is PolicyOutcome.ALLOWED,
			outcome=outcome,
			reason=reason,
			url=url,
			source_id=source_id,
			robots_url=robots_url,
			user_agent=CRAWLER_USER_AGENT,
		)