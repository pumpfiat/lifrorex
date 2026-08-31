from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment

from app.content.document import Document, ExtractionStatus
from app.content.metadata import MetadataExtractor


class HtmlContentExtractor:
	_IGNORED_TAGS = {"script", "style", "noscript", "template", "svg", "iframe", "object", "embed"}

	def extract(self, html: str | None) -> str:
		if html is None:
			return ""
		if not isinstance(html, str):
			html = str(html)
		if not html.strip():
			return ""

		soup = BeautifulSoup(html, "html.parser")
		for tag_name in self._IGNORED_TAGS:
			for tag in soup.find_all(tag_name):
				tag.decompose()
		# Was nested inside the tag-name loop above, re-scanning the whole
		# document for comments once per ignored tag name (8x redundant work
		# per document). Comments only need removing once, after all ignored
		# tags are gone.
		for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
			comment.extract()

		text = "\n\n".join(part.strip() for part in soup.stripped_strings if part.strip())
		text = re.sub(r"\n\s*\n+", "\n\n", text)
		text = re.sub(r"[ \t]+", " ", text)
		text = re.sub(r"\n +", "\n", text)
		text = re.sub(r" +\n", "\n", text)
		return text.strip()

	def extract_title(self, html: str | None) -> str | None:
		if html is None or not isinstance(html, str) or not html.strip():
			return None
		try:
			soup = BeautifulSoup(html, "html.parser")
		except Exception:
			return None
		title = soup.title
		if title is None:
			return None
		value = title.get_text(" ", strip=True)
		return value or None

	def extract_document(
		self,
		source_url: str,
		*,
		source_id: int | None = None,
		canonical_url: str | None = None,
		content_type: str | None = None,
		http_status: int | None = None,
		html: str | None = None,
	) -> Document:
		normalized_content_type = content_type.split(";", maxsplit=1)[0].strip().lower() if content_type else None
		# application/xhtml+xml is real, valid, well-formed HTML that
		# BeautifulSoup parses fine -- previously only exact "text/html" was
		# accepted, silently dropping any site serving XHTML.
		if normalized_content_type is not None and normalized_content_type not in {"text/html", "application/xhtml+xml"}:
			return Document(
				source_id=source_id,
				source_url=source_url,
				canonical_url=canonical_url,
				content="",
				content_type=content_type,
				http_status=http_status,
				extraction_status=ExtractionStatus.UNSUPPORTED,
				metadata={"reason": "non_html_content_type"},
			)

		try:
			content = self.extract(html)
			extraction_status = ExtractionStatus.SUCCESS
		except Exception:
			return Document(
				source_id=source_id,
				source_url=source_url,
				canonical_url=canonical_url,
				content="",
				content_type=content_type or "text/html",
				http_status=http_status,
				extraction_status=ExtractionStatus.FAILED,
				metadata={"reason": "html_extraction_failed"},
			)

		# title is intentionally left unset here (not pulled from the plain
		# <title> tag) so MetadataExtractor.extract_document_metadata below
		# -- which prioritizes JSON-LD / Open Graph over a plain <title> tag
		# that's often polluted with a site-name suffix -- gets first say.
		# Previously this method set title from the plain tag immediately,
		# which meant the "only fill if still None" merge in metadata
		# extraction could never actually override it with anything better.
		document = Document(
			source_id=source_id,
			source_url=source_url,
			canonical_url=canonical_url,
			content=content,
			content_type=content_type or "text/html",
			http_status=http_status,
			extraction_status=extraction_status,
			metadata={"html_extracted": True},
		)
		return MetadataExtractor.extract_document_metadata(document, html)


def extract_html_text(html: str | None) -> str:
	return HtmlContentExtractor().extract(html)


def extract_document(
	source_url: str,
	*,
	source_id: int | None = None,
	canonical_url: str | None = None,
	content_type: str | None = None,
	http_status: int | None = None,
	html: str | None = None,
) -> Document:
	return HtmlContentExtractor().extract_document(
		source_url,
		source_id=source_id,
		canonical_url=canonical_url,
		content_type=content_type,
		http_status=http_status,
		html=html,
	)
