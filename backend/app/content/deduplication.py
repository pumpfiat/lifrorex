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
	if content is None:
		return "empty"
	normalized = _normalize_document_text(content)
	if not normalized:
		return "empty"
	return normalized


def fingerprint_document(document: Document) -> str:
	if document is None:
		return "empty"
	content = document.content or ""
	normalized = fingerprint_document_content(content)
	if normalized == "empty":
		return "empty"
	return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


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
