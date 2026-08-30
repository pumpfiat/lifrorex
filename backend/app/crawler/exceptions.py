class CrawlerError(Exception):
	"""Base exception for crawler subsystem failures."""


class FetchError(CrawlerError):
	"""Raised when a future fetch operation cannot complete."""


class PolicyError(CrawlerError):
	"""Raised when future crawl policy evaluation fails."""


class DiscoveryError(CrawlerError):
	"""Raised when future URL discovery cannot complete."""