from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.content.document import Document


class MetadataExtractor:
	def extract_metadata(self, html: str, source_url: str) -> dict[str, Any]:
		if not html or not html.strip():
			return {}

		soup = BeautifulSoup(html, "html.parser")
		metadata: dict[str, Any] = {
			"title": self._extract_title(soup),
			"description": self._extract_description(soup),
			"canonical_url": self._extract_canonical_url(soup, source_url),
			"author": self._extract_author(soup),
			"published_at": self._extract_datetime(soup, "article:published_time"),
			"modified_at": self._extract_datetime(soup, "article:modified_time"),
			"metadata": {},
		}

		json_ld = self._extract_json_ld(soup)
		if json_ld:
			metadata["metadata"]["json_ld"] = json_ld
			metadata = self._apply_json_ld_overrides(metadata, json_ld, source_url)

		if metadata.get("title") is None:
			fallback_title = self._extract_og_value(soup, "og:title")
			if fallback_title:
				metadata["title"] = fallback_title

		if metadata.get("description") is None:
			fallback_description = self._extract_og_value(soup, "og:description")
			if fallback_description:
				metadata["description"] = fallback_description

		if metadata.get("canonical_url") is None:
			fallback_canonical = self._extract_og_value(soup, "og:url")
			if fallback_canonical:
				metadata["canonical_url"] = self._resolve_url(fallback_canonical, source_url)

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
				parsed = datetime.fromisoformat(candidate)
			except ValueError:
				continue
			if parsed.tzinfo is None:
				return parsed.replace(tzinfo=None)
			return parsed.astimezone()
		return None

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
	def _apply_json_ld_overrides(metadata: dict[str, Any], candidate: Any, source_url: str) -> dict[str, Any]:
		items: list[Any] = []
		if isinstance(candidate, list):
			items.extend(candidate)
		else:
			items.append(candidate)

		for item in items:
			for obj in MetadataExtractor._iter_json_ld_objects(item):
				title_value = None
				for key in ("headline", "name"):
					value = obj.get(key)
					if value:
						title_value = MetadataExtractor._normalize_text(str(value))
						break
				if title_value and metadata.get("title") is None:
					metadata["title"] = title_value
				if "description" in obj and metadata.get("description") is None:
					metadata["description"] = MetadataExtractor._normalize_text(str(obj["description"]))
				if "author" in obj and metadata.get("author") is None:
					author = MetadataExtractor._extract_json_ld_author(obj["author"])
					if author:
						metadata["author"] = author
				if "datePublished" in obj and metadata.get("published_at") is None:
					parsed = MetadataExtractor._parse_datetime(str(obj["datePublished"]))
					if parsed is not None:
						metadata["published_at"] = parsed
				if "dateModified" in obj and metadata.get("modified_at") is None:
					parsed = MetadataExtractor._parse_datetime(str(obj["dateModified"]))
					if parsed is not None:
						metadata["modified_at"] = parsed
				if "url" in obj and metadata.get("canonical_url") is None:
					candidate_url = MetadataExtractor._resolve_url(str(obj["url"]), source_url)
					if candidate_url:
						metadata["canonical_url"] = candidate_url
		return metadata

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
