from enum import StrEnum


CRAWLER_USER_AGENT = "LiforexBot/0.1"


class CrawlOutcome(StrEnum):
	SUCCESS = "success"
	BLOCKED = "blocked"
	DISALLOWED = "disallowed"
	NOT_FOUND = "not_found"
	CLIENT_ERROR = "client_error"
	SERVER_ERROR = "server_error"
	TIMEOUT = "timeout"
	CONNECTION_ERROR = "connection_error"
	INVALID_RESPONSE = "invalid_response"
	UNKNOWN_ERROR = "unknown_error"


class PolicyOutcome(StrEnum):
	ALLOWED = "allowed"
	DISALLOWED = "disallowed"
	UNKNOWN = "unknown"


class PolicyReason(StrEnum):
	SOURCE_INACTIVE = "source_inactive"
	SOURCE_CRAWL_NOT_ALLOWED = "source_crawl_not_allowed"
	INVALID_URL = "invalid_url"
	UNSUPPORTED_SCHEME = "unsupported_scheme"
	CROSS_ORIGIN = "cross_origin"
	ROBOTS_ALLOWED = "robots_allowed"
	ROBOTS_DISALLOWED = "robots_disallowed"
	ROBOTS_MISSING = "robots_missing"
	ROBOTS_UNAVAILABLE = "robots_unavailable"
	ROBOTS_INVALID = "robots_invalid"