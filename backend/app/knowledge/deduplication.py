"""Deterministic comparison helpers for obvious knowledge duplicates.

This module intentionally detects only identical knowledge content after
normalization. It does not attempt semantic equivalence or similarity matching.
"""

import hashlib
import unicodedata


_TERMINAL_PUNCTUATION = ".!?"


def normalize_knowledge_content(content: str) -> str:
	"""Return a stable comparison value without changing stored source wording."""
	if not isinstance(content, str):
		raise TypeError("content must be a string")

	normalized = unicodedata.normalize("NFKC", content).casefold()
	normalized = " ".join(normalized.split())
	return normalized.rstrip(_TERMINAL_PUNCTUATION).rstrip()


def knowledge_fingerprint(content: str) -> str:
	"""Return the SHA-256 fingerprint of normalized knowledge content."""
	normalized = normalize_knowledge_content(content)
	if not normalized:
		raise ValueError("content must not be blank")
	return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


__all__ = ["knowledge_fingerprint", "normalize_knowledge_content"]