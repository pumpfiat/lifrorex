from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.content.classification import classify_document
from app.content.document import Document


_SCORE_MIN = 0.0
_SCORE_MAX = 1.0


@dataclass(frozen=True)
class ScoreResult:
	quality: float
	relevance: float
	quality_level: str
	relevance_level: str
	quality_evidence: list[str] = field(default_factory=list)
	relevance_evidence: list[str] = field(default_factory=list)


class DocumentScorer:
	_TITLE_WEAK = {"home", "page", "untitled", "loading", "index", "about", "contact"}
	_RELEVANCE_TERMS: list[tuple[str, float]] = [
		("foreign exchange", 1.0),
		("forex", 1.0),
		("fx", 0.9),
		("divisas", 0.9),
		("derivatives", 1.0),
		("swap", 0.9),
		("swaps", 0.9),
		("currency", 0.8),
		("currencies", 0.8),
		("exchange rate", 0.8),
		("financial regulation", 0.9),
		("regulatory", 0.8),
		("compliance", 0.7),
		("market risk", 0.9),
		("risk management", 0.9),
		("monetary policy", 0.9),
		("política monetaria", 0.9),
		("central bank", 0.9),
		("interest rate", 0.8),
		("interest rates", 0.8),
		("financial markets", 0.9),
		("mercados financieros", 0.9),
		("trading", 0.7),
		("liquidity", 0.7),
		("commodities", 0.8),
		("futures", 0.8),
		("options", 0.7),
		("broker", 0.6),
		("banking", 0.6),
		("riesgo", 0.7),
		("riesgo financiero", 0.9),
		("mercados", 0.5),
		("macro", 0.5),
		("risk", 0.25),
		("market", 0.18),
		("report", 0.18),
		("business", 0.1),
		("information", 0.1),
	]

	@staticmethod
	def normalize_text(value: Any) -> str:
		if value is None:
			return ""
		if not isinstance(value, str):
			value = str(value)
		return re.sub(r"\s+", " ", value.strip().lower())

	@staticmethod
	def _tokenize(text: str) -> set[str]:
		return {token for token in re.findall(r"[a-z0-9]+(?:[\-/][a-z0-9]+)*", text.lower()) if token}

	@classmethod
	def _score_quality(cls, document: Document) -> tuple[float, list[str]]:
		quality_parts: list[str] = []
		score = 0.0

		if document.title:
			title = cls.normalize_text(document.title)
			if title and title not in cls._TITLE_WEAK:
				score += 0.20
				quality_parts.append("meaningful title")
			else:
				score += 0.05
				quality_parts.append("weak title")
		else:
			quality_parts.append("missing title")

		content = cls.normalize_text(document.content)
		if content:
			word_count = len(content.split())
			if word_count >= 80:
				score += 0.45
				quality_parts.append("substantive content")
			elif word_count >= 20:
				score += 0.35
				quality_parts.append("moderate content")
			elif word_count >= 10:
				score += 0.20
				quality_parts.append("brief content")
			else:
				score += 0.10
				quality_parts.append("very brief content")
		else:
			quality_parts.append("empty content")
			score -= 0.30

		content_tokens = cls._tokenize(content)
		if content_tokens and len(content_tokens) > 0:
			unique_ratio = len(set(content_tokens)) / len(content_tokens)
			strong_domain_markers = {"foreign exchange", "forex", "derivatives", "swap", "risk management", "financial regulation", "divisas", "riesgo financiero", "central bank", "interest rate", "monetary policy"}
			if unique_ratio < 0.35 and not any(marker in content for marker in strong_domain_markers):
				score -= 0.20
				quality_parts.append("repetitive boilerplate detected")
			if len(content.split()) >= 35 and any(marker in content for marker in strong_domain_markers):
				score += 0.15
				quality_parts.append("domain-rich substantial content")

		if document.canonical_url:
			score += 0.05
			quality_parts.append("canonical url present")
		if document.published_at is not None:
			score += 0.05
			quality_parts.append("publication date present")
		if document.author:
			score += 0.05
			quality_parts.append("author present")
		if document.description:
			score += 0.08
			quality_parts.append("description present")

		if getattr(document, "extraction_status", None) is not None:
			if str(document.extraction_status).lower() == "success":
				score += 0.08
				quality_parts.append("successful extraction")
			elif str(document.extraction_status).lower() in {"failed", "unsupported"}:
				score -= 0.20
				quality_parts.append("extraction issue")

		if document.metadata:
			score += 0.04
			quality_parts.append("metadata present")

		classification = classify_document(document)
		if classification.document_type != "other":
			score += 0.05
			quality_parts.append(f"classification: {classification.document_type}")

		if text := cls.normalize_text(document.content):
			if len(text.split()) < 12 and not document.title:
				score -= 0.15
				quality_parts.append("insufficient document substance")

		final_score = min(max(score, _SCORE_MIN), _SCORE_MAX)
		return final_score, quality_parts

	@classmethod
	def _score_relevance(cls, document: Document) -> tuple[float, list[str]]:
		title = cls.normalize_text(document.title)
		description = cls.normalize_text(document.description)
		content = cls.normalize_text(document.content)
		url = cls.normalize_text(document.canonical_url or document.source_url)
		combined = " ".join(part for part in [title, description, content, url] if part)
		if not combined:
			return 0.0, ["no relevance signals"]

		relevance_score = 0.0
		evidence: list[str] = []
		seen_terms: set[str] = set()
		for term, weight in cls._RELEVANCE_TERMS:
			if term in combined:
				term_count = combined.count(term)
				contribution = min(weight * min(term_count, 2) / 2, weight * 0.8)
				relevance_score += contribution
				if term not in seen_terms:
					evidence.append(f"contains '{term}'")
					seen_terms.add(term)

		if title:
			for term, weight in cls._RELEVANCE_TERMS:
				if term in title:
					relevance_score += weight * 0.30
					if term not in seen_terms:
						evidence.append(f"title contains '{term}'")
						seen_terms.add(term)

		if document.description:
			for term, weight in cls._RELEVANCE_TERMS:
				if term in description:
					relevance_score += weight * 0.12
					if term not in seen_terms:
						evidence.append(f"description contains '{term}'")
						seen_terms.add(term)

		classification = classify_document(document)
		if classification.document_type in {"regulation", "guidance", "enforcement", "market_report", "research", "speech", "testimony", "rulemaking", "notice"}:
			relevance_score += 0.12
			evidence.append(f"classification: {classification.document_type}")

		if relevance_score <= 0.0:
			return 0.0, ["no relevance signals"]

		final_score = relevance_score / 2.4
		final_score = min(max(final_score, _SCORE_MIN), 0.8)
		if not evidence:
			evidence = ["no relevance signals"]
		return round(final_score, 4), evidence

	@classmethod
	def classify(cls, document: Document) -> ScoreResult:
		quality_score, quality_evidence = cls._score_quality(document)
		relevance_score, relevance_evidence = cls._score_relevance(document)
		return ScoreResult(
			quality=round(quality_score, 4),
			relevance=round(relevance_score, 4),
			quality_level=cls._label(quality_score),
			relevance_level=cls._label(relevance_score),
			quality_evidence=quality_evidence,
			relevance_evidence=relevance_evidence,
		)

	@staticmethod
	def _label(score: float) -> str:
		if score >= 0.7:
			return "high"
		if score >= 0.4:
			return "medium"
		return "low"


def score_document(document: Document) -> ScoreResult:
	return DocumentScorer.classify(document)


__all__ = [
	"DocumentScorer",
	"ScoreResult",
	"score_document",
]
