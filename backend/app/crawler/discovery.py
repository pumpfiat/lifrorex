from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.crawler.exceptions import DiscoveryError, UrlNormalizationError
from app.crawler.urls import HttpUrlNormalizer


class HtmlLinkDiscoverer:
	def __init__(self, url_normalizer: HttpUrlNormalizer | None = None) -> None:
		self.url_normalizer = url_normalizer or HttpUrlNormalizer()

	def discover(self, content: bytes, base_url: str) -> tuple[str, ...]:
		try:
			document_url = self.url_normalizer.normalize(base_url).canonical
		except UrlNormalizationError as error:
			raise DiscoveryError("document URL must be an absolute HTTP(S) URL") from error

		parser = _AnchorParser(document_url)
		parser.feed(content.decode("utf-8", errors="replace"))
		parser.close()
		return tuple(parser.candidates)


class _AnchorParser(HTMLParser):
	def __init__(self, document_url: str) -> None:
		super().__init__(convert_charrefs=True)
		self.document_url = document_url
		self.resolution_base = document_url
		self._base_seen = False
		self.candidates: list[str] = []
		self._seen: set[str] = set()

	def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		attributes = dict(attrs)
		if tag.casefold() == "base":
			self._set_base(attributes.get("href"))
		elif tag.casefold() == "a":
			self._add_link(attributes.get("href"))

	def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
		self.handle_starttag(tag, attrs)

	def _set_base(self, href: str | None) -> None:
		if self._base_seen or href is None:
			return
		self._base_seen = True
		candidate = href.strip()
		if not candidate or self._is_unsupported_scheme(candidate):
			return
		resolved = urljoin(self.document_url, candidate)
		if urlsplit(resolved).scheme in {"http", "https"}:
			self.resolution_base = resolved

	def _add_link(self, href: str | None) -> None:
		if href is None:
			return
		candidate = href.strip()
		if not candidate or self._is_unsupported_scheme(candidate):
			return
		resolved = urljoin(self.resolution_base, candidate)
		if urlsplit(resolved).scheme not in {"http", "https"} or resolved in self._seen:
			return
		self._seen.add(resolved)
		self.candidates.append(resolved)

	@staticmethod
	def _is_unsupported_scheme(url: str) -> bool:
		scheme = urlsplit(url).scheme.casefold()
		return bool(scheme) and scheme not in {"http", "https"}