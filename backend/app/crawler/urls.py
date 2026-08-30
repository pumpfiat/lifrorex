from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from app.crawler.exceptions import UrlNormalizationError


@dataclass(frozen=True, slots=True)
class NormalizedUrl:
	original: str
	canonical: str
	scheme: str
	host: str
	port: int | None
	path: str
	query: str


class HttpUrlNormalizer:
	def normalize(self, url: str) -> NormalizedUrl:
		parsed = urlsplit(url)
		scheme = parsed.scheme.lower()
		if scheme not in {"http", "https"}:
			raise UrlNormalizationError(self._scheme_error(scheme))
		if not parsed.netloc:
			raise UrlNormalizationError("absolute HTTP(S) URL required")
		if parsed.username is not None or parsed.password is not None:
			raise UrlNormalizationError("URL userinfo is not allowed")

		try:
			host = parsed.hostname
			port = parsed.port
		except ValueError as error:
			raise UrlNormalizationError("invalid URL port") from error
		if host is None or "%" in host:
			raise UrlNormalizationError("invalid URL host")

		try:
			host = host.encode("idna").decode("ascii").lower()
		except UnicodeError as error:
			raise UrlNormalizationError("invalid URL host") from error

		if port == 80 and scheme == "http" or port == 443 and scheme == "https":
			port = None
		netloc = f"[{host}]" if ":" in host else host
		if port is not None:
			netloc = f"{netloc}:{port}"

		path = self._normalize_path(parsed.path)
		canonical = urlunsplit((scheme, netloc, path, parsed.query, ""))
		return NormalizedUrl(url, canonical, scheme, host, port, path, parsed.query)

	@staticmethod
	def _scheme_error(scheme: str) -> str:
		return "unsupported URL scheme" if scheme else "absolute HTTP(S) URL required"

	@staticmethod
	def _normalize_path(path: str) -> str:
		if not path:
			return "/"

		segments: list[str] = []
		for segment in path.split("/"):
			if segment == ".":
				continue
			if segment == "..":
				if segments:
					segments.pop()
				continue
			segments.append(segment)

		normalized = "/".join(segments)
		if not normalized.startswith("/"):
			normalized = f"/{normalized}"
		if path.endswith(("/", "/.", "/..")) and not normalized.endswith("/"):
			normalized = f"{normalized}/"
		return normalized


class InMemoryUrlDeduplicator:
	def __init__(self) -> None:
		self._seen: set[str] = set()

	def check_and_mark(self, url: NormalizedUrl) -> bool:
		if url.canonical in self._seen:
			return False
		self._seen.add(url.canonical)
		return True

	def is_seen(self, url: NormalizedUrl) -> bool:
		return url.canonical in self._seen