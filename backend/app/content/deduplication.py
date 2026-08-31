from __future__ import annotations

import hashlib
import re
from typing import Any

from app.content.document import Document


FINGERPRINT_VERSION = "v1"


def _normalize_document_text(value: Any) -> str:
	if value is None:
		return ""
	if not isinstance(value, str):
		value = str(value)
	text = value.replace("\r\n", "\n").replace("\r", "\n")
	text = re.sub(r"\s+", " ", text).strip()
	return text


def fingerprint_document_content(content: str | None) -> str:
	"""Compute the SHA-256 fingerprint hash for a raw content string.

	Returns "empty" (a sentinel, not a hash) for None/whitespace-only
	content, so callers can distinguish "nothing to fingerprint" from a
	real hash value. Previously this returned the raw normalized TEXT
	instead of a hash despite the name and being publicly exported --
	calling it directly handed back a potentially huge unbounded string
	instead of a compact fingerprint, and its result didn't match what
	fingerprint_document() actually produced for the same content.
	"""
	if content is None:
		return "empty"
	normalized = _normalize_document_text(content)
	if not normalized:
		return "empty"
	return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def fingerprint_document(document: Document) -> str:
	if document is None:
		return "empty"
	return fingerprint_document_content(document.content or "")


def deduplicate_documents(document_a: Document, document_b: Document) -> bool:
	if document_a is None or document_b is None:
		return False
	return fingerprint_document(document_a) == fingerprint_document(document_b)


def is_duplicate(document_a: Document, document_b: Document) -> bool:
	return deduplicate_documents(document_a, document_b)


__all__ = [
	"FINGERPRINT_VERSION",
	"deduplicate_documents",
	"fingerprint_document",
	"fingerprint_document_content",
	"is_duplicate",
]
