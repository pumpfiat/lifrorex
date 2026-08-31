from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.content.document import Document


class MetadataExtractor:
	def extract_metadata(self, html: str, source_url: str) -> dict[str, Any]:
		if not html or not html.strip():
			return {}

		soup = BeautifulSoup(html, "html.parser")

		json_ld = self._extract_json_ld(soup)
		json_ld_fields = self._json_ld_fields(json_ld, source_url) if json_ld else {}

		# Explicit priority: JSON-LD structured data first (deliberately
		# curated by the publisher for machine consumption), then Open Graph
		# (meant for rich sharing previews, usually clean), then the plain
		# <title>/<meta name="description"> tags last -- these are often
		# polluted with a site-name suffix ("Page Title | Site Name") or are
		# just less reliable than the other two sources when they're present.
		# Previously each source was applied in sequence with an "only if
		# still unset" check, but the plain-tag values were computed and
		# assigned first, so they always won by default regardless of
		# whether a better JSON-LD or OG value existed.
		title = (
			json_ld_fields.get("title")
			or self._extract_og_value(soup, "og:title")
			or self._extract_title(soup)
		)
		description = (
			json_ld_fields.get("description")
			or self._extract_og_value(soup, "og:description")
			or self._extract_description(soup)
		)
		og_url = self._extract_og_value(soup, "og:url")
		canonical_url = (
			json_ld_fields.get("canonical_url")
			or (self._resolve_url(og_url, source_url) if og_url else None)
			or self._extract_canonical_url(soup, source_url)
		)
		author = json_ld_fields.get("author") or self._extract_author(soup)
		published_at = json_ld_fields.get("published_at") or self._extract_datetime(
			soup, "article:published_time"
		)
		modified_at = json_ld_fields.get("modified_at") or self._extract_datetime(
			soup, "article:modified_time"
		)

		metadata: dict[str, Any] = {
			"title": title,
			"description": description,
			"canonical_url": canonical_url,
			"author": author,
			"published_at": published_at,
			"modified_at": modified_at,
			"metadata": {"json_ld": json_ld} if json_ld else {},
		}
		return {key: value for key, value in metadata.items() if value is not None}

	@staticmethod
	def extract_document_metadata(document: Document, html: str | None) -> Document:
		if html is None or not html.strip():
			return document
		metadata = MetadataExtractor().extract_metadata(html, document.source_url)
		if "title" in metadata and document.title is None:
			document.title = metadata["title"]
		if "description" in metadata and getattr(document, "description", None) is None:
			document.description = metadata["description"]
		if "author" in metadata and getattr(document, "author", None) is None:
			document.author = metadata["author"]
		if "published_at" in metadata and getattr(document, "published_at", None) is None:
			document.published_at = metadata["published_at"]
		if "modified_at" in metadata and getattr(document, "modified_at", None) is None:
			document.modified_at = metadata["modified_at"]
		if "canonical_url" in metadata:
			document.canonical_url = metadata["canonical_url"]
		return document

	@staticmethod
	def _normalize_text(value: str | None) -> str | None:
		if value is None:
			return None
		text = " ".join(value.split())
		return text or None

	@staticmethod
	def _resolve_url(candidate: str, source_url: str) -> str | None:
		value = candidate.strip()
		if not value or any(ch.isspace() for ch in value):
			return None
		resolved = urljoin(source_url, value)
		parsed = urlsplit(resolved)
		if parsed.scheme not in {"http", "https"} or not parsed.netloc:
			return None
		return resolved

	@staticmethod
	def _extract_title(soup: BeautifulSoup) -> str | None:
		title = soup.title
		if title is None:
			return None
		return MetadataExtractor._normalize_text(title.get_text(" ", strip=True))

	@staticmethod
	def _extract_description(soup: BeautifulSoup) -> str | None:
		for selector in ("meta[name='description']", 'meta[name="description"]', 'meta[property="og:description"]'):
			value = soup.select_one(selector)
			if value is not None and value.get("content"):
				return MetadataExtractor._normalize_text(value["content"])
		return None

	@staticmethod
	def _extract_author(soup: BeautifulSoup) -> str | None:
		for selector in ("meta[name='author']", 'meta[name="author"]', 'meta[property="article:author"]'):
			value = soup.select_one(selector)
			if value is not None and value.get("content"):
				return MetadataExtractor._normalize_text(value["content"])
		return None

	@staticmethod
	def _extract_canonical_url(soup: BeautifulSoup, source_url: str) -> str | None:
		link = soup.select_one('link[rel="canonical"]')
		if link is None:
			return None
		value = link.get("href")
		if not value:
			return None
		return MetadataExtractor._resolve_url(value, source_url)

	@staticmethod
	def _extract_datetime(soup: BeautifulSoup, property_name: str) -> datetime | None:
		selector = f'meta[property="{property_name}"]'
		value = soup.select_one(selector)
		if value is None or not value.get("content"):
			return None
		text = value["content"].strip()
		return MetadataExtractor._parse_datetime(text)

	@staticmethod
	def _parse_datetime(value: str) -> datetime | None:
		text = value.strip()
		if not text:
			return None
		for candidate in (text, text.replace("Z", "+00:00")):
			try:
				return datetime.fromisoformat(candidate)
			except ValueError:
				continue
		# ISO-8601 didn't match -- try RFC 2822 ("Mon, 15 Jan 2024 10:00:00
		# GMT"), which is common in feed-adjacent meta tags even outside
		# actual RSS/Atom documents. Uses the stdlib parser, no new
		# dependency. Previously any non-ISO date silently returned None
		# here, quietly losing publish dates on a real subset of sources.
		try:
			parsed = parsedate_to_datetime(text)
		except (TypeError, ValueError):
			return None
		return parsed

	@staticmethod
	def _extract_og_value(soup: BeautifulSoup, property_name: str) -> str | None:
		value = soup.select_one(f'meta[property="{property_name}"]')
		if value is None or not value.get("content"):
			return None
		return MetadataExtractor._normalize_text(value["content"])

	@staticmethod
	def _extract_json_ld(soup: BeautifulSoup) -> dict[str, Any] | list[Any] | None:
		blocks = soup.select('script[type="application/ld+json"]')
		candidates: list[Any] = []
		for block in blocks:
			content = block.get_text(strip=True)
			if not content:
				continue
			try:
				parsed = json.loads(content)
			except json.JSONDecodeError:
				continue
			if parsed is not None:
				candidates.append(parsed)
		if not candidates:
			return None
		if len(candidates) == 1:
			return candidates[0]
		return candidates

	@staticmethod
	def _json_ld_fields(candidate: Any, source_url: str) -> dict[str, Any]:
		"""Extract title/description/author/dates/canonical_url from JSON-LD,
		if present. Within JSON-LD itself, first object found wins for each
		field (reasonable -- multiple JSON-LD blocks describing the same page
		are rare). Returns only the fields actually found; the caller decides
		priority against other sources (Open Graph, plain tags)."""
		items: list[Any] = candidate if isinstance(candidate, list) else [candidate]
		fields: dict[str, Any] = {}

		for item in items:
			for obj in MetadataExtractor._iter_json_ld_objects(item):
				if "title" not in fields:
					for key in ("headline", "name"):
						value = obj.get(key)
						if value:
							fields["title"] = MetadataExtractor._normalize_text(str(value))
							break
				if "description" not in fields and obj.get("description"):
					fields["description"] = MetadataExtractor._normalize_text(str(obj["description"]))
				if "author" not in fields and "author" in obj:
					author = MetadataExtractor._extract_json_ld_author(obj["author"])
					if author:
						fields["author"] = author
				if "published_at" not in fields and obj.get("datePublished"):
					parsed = MetadataExtractor._parse_datetime(str(obj["datePublished"]))
					if parsed is not None:
						fields["published_at"] = parsed
				if "modified_at" not in fields and obj.get("dateModified"):
					parsed = MetadataExtractor._parse_datetime(str(obj["dateModified"]))
					if parsed is not None:
						fields["modified_at"] = parsed
				if "canonical_url" not in fields and obj.get("url"):
					candidate_url = MetadataExtractor._resolve_url(str(obj["url"]), source_url)
					if candidate_url:
						fields["canonical_url"] = candidate_url
		return fields

	@staticmethod
	def _iter_json_ld_objects(value: Any) -> Iterable[Mapping[str, Any]]:
		if isinstance(value, Mapping):
			if "@graph" in value:
				for item in value["@graph"]:
					yield from MetadataExtractor._iter_json_ld_objects(item)
			else:
				yield value
		elif isinstance(value, list):
			for item in value:
				yield from MetadataExtractor._iter_json_ld_objects(item)

	@staticmethod
	def _extract_json_ld_author(author: Any) -> str | None:
		if isinstance(author, str):
			return MetadataExtractor._normalize_text(author)
		if isinstance(author, Mapping):
			for key in ("name", "givenName"):
				if key in author:
					return MetadataExtractor._normalize_text(str(author[key]))
		if isinstance(author, list):
			for item in author:
				value = MetadataExtractor._extract_json_ld_author(item)
				if value:
					return value
		return None


def extract_metadata(html: str, source_url: str) -> dict[str, Any]:
	return MetadataExtractor().extract_metadata(html, source_url)
