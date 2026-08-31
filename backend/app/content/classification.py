from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.content.document import Document


class ClassificationConfidence(str, Enum):
	HIGH = "HIGH"
	MEDIUM = "MEDIUM"
	LOW = "LOW"


DOCUMENT_TYPES = {
	"regulation",
	"guidance",
	"enforcement",
	"press_release",
	"market_report",
	"research",
	"speech",
	"testimony",
	"rulemaking",
	"notice",
	"other",
}


@dataclass(frozen=True)
class ClassificationResult:
	document_type: str
	confidence: ClassificationConfidence
	matched_rules: list[str] = field(default_factory=list)
	evidence: list[str] = field(default_factory=list)


class DocumentClassifier:
	_TITLE_RULES: list[tuple[str, str, ClassificationConfidence]] = [
		("press release", "press_release", ClassificationConfidence.HIGH),
		("for immediate release", "press_release", ClassificationConfidence.HIGH),
		("final rule", "regulation", ClassificationConfidence.HIGH),
		("final rules", "regulation", ClassificationConfidence.HIGH),
		("proposed rulemaking", "rulemaking", ClassificationConfidence.HIGH),
		("notice of proposed action", "notice", ClassificationConfidence.HIGH),
		("notice of proposed rulemaking", "notice", ClassificationConfidence.HIGH),
		("enforcement action", "enforcement", ClassificationConfidence.HIGH),
		("staff guidance", "guidance", ClassificationConfidence.HIGH),
		("guidance on", "guidance", ClassificationConfidence.HIGH),
		("market report", "market_report", ClassificationConfidence.HIGH),
		("research report", "research", ClassificationConfidence.HIGH),
		("remarks by the chair", "speech", ClassificationConfidence.HIGH),
		("speech by", "speech", ClassificationConfidence.HIGH),
		("testimony before", "testimony", ClassificationConfidence.HIGH),
		("testimony of", "testimony", ClassificationConfidence.HIGH),
		("proposed rule", "rulemaking", ClassificationConfidence.HIGH),
		("adopted final rule", "regulation", ClassificationConfidence.HIGH),
		("rulemaking on", "rulemaking", ClassificationConfidence.HIGH),
	]

	_DESCRIPTION_RULES: list[tuple[str, str, ClassificationConfidence]] = [
		("final rule", "regulation", ClassificationConfidence.MEDIUM),
		("issued a final rule", "regulation", ClassificationConfidence.MEDIUM),
		("adopting a final rule", "regulation", ClassificationConfidence.MEDIUM),
		("staff guidance", "guidance", ClassificationConfidence.MEDIUM),
		("enforcement action", "enforcement", ClassificationConfidence.MEDIUM),
		("for immediate release", "press_release", ClassificationConfidence.MEDIUM),
		("market report", "market_report", ClassificationConfidence.MEDIUM),
		("research report", "research", ClassificationConfidence.MEDIUM),
		("testimony before", "testimony", ClassificationConfidence.MEDIUM),
		("remarks by", "speech", ClassificationConfidence.MEDIUM),
		("proposed rulemaking", "rulemaking", ClassificationConfidence.MEDIUM),
		("notice of proposed action", "notice", ClassificationConfidence.MEDIUM),
	]

	_URL_RULES: list[tuple[str, str, ClassificationConfidence]] = [
		("/press-releases/", "press_release", ClassificationConfidence.MEDIUM),
		("/press_release/", "press_release", ClassificationConfidence.MEDIUM),
		("/enforcement/", "enforcement", ClassificationConfidence.MEDIUM),
		("/guidance/", "guidance", ClassificationConfidence.MEDIUM),
		("/speeches/", "speech", ClassificationConfidence.MEDIUM),
		("/testimony/", "testimony", ClassificationConfidence.MEDIUM),
		("/rulemaking/", "rulemaking", ClassificationConfidence.MEDIUM),
		("/notices/", "notice", ClassificationConfidence.MEDIUM),
		("/research/", "research", ClassificationConfidence.MEDIUM),
		("/market-report/", "market_report", ClassificationConfidence.MEDIUM),
		("/market-reports/", "market_report", ClassificationConfidence.MEDIUM),
		("/rules/", "regulation", ClassificationConfidence.MEDIUM),
		("/regulations/", "regulation", ClassificationConfidence.MEDIUM),
	]

	_CONTENT_RULES: list[tuple[str, str, ClassificationConfidence]] = [
		("final rule", "regulation", ClassificationConfidence.LOW),
		("proposed rulemaking", "rulemaking", ClassificationConfidence.LOW),
		("enforcement action", "enforcement", ClassificationConfidence.LOW),
		("staff guidance", "guidance", ClassificationConfidence.LOW),
		("for immediate release", "press_release", ClassificationConfidence.LOW),
		("market report", "market_report", ClassificationConfidence.LOW),
		("research report", "research", ClassificationConfidence.LOW),
		("testimony before", "testimony", ClassificationConfidence.LOW),
		("remarks by the chair", "speech", ClassificationConfidence.LOW),
		("notice of proposed action", "notice", ClassificationConfidence.LOW),
	]

	@staticmethod
	def normalize_text(value: Any) -> str:
		if value is None:
			return ""
		if not isinstance(value, str):
			value = str(value)
		return " ".join(value.strip().lower().split())

	@classmethod
	def _matches(cls, source: str, rules: list[tuple[str, str, ClassificationConfidence]]) -> list[tuple[str, ClassificationConfidence]]:
		matches: list[tuple[str, ClassificationConfidence]] = []
		normalized = cls.normalize_text(source)
		for needle, document_type, confidence in rules:
			if needle in normalized:
				matches.append((document_type, confidence))
		return matches

	@classmethod
	def classify(cls, document: Document) -> ClassificationResult:
		if document is None:
			return ClassificationResult(document_type="other", confidence=ClassificationConfidence.LOW, matched_rules=["empty-document"], evidence=["document missing"])

		text_parts: list[str] = []
		for value in (document.title, document.description, document.metadata.get("description"), document.content, document.source_url, document.canonical_url):
			if isinstance(value, str) and value.strip():
				text_parts.append(value)
		combined_text = " ".join(text_parts)
		if not combined_text.strip():
			return ClassificationResult(document_type="other", confidence=ClassificationConfidence.LOW, matched_rules=["empty-document"], evidence=["no title, description, content, or URL text available"])

		title_text = cls.normalize_text(document.title)
		description_text = cls.normalize_text(document.description)
		url_text = cls.normalize_text(document.canonical_url or document.source_url)
		content_text = cls.normalize_text(document.content)

		try:
			rule_matches: list[tuple[str, ClassificationConfidence, str]] = []
			for marker, document_type, confidence in cls._TITLE_RULES:
				if marker in title_text:
					rule_matches.append((document_type, confidence, f"title contains '{marker}'"))
			for marker, document_type, confidence in cls._DESCRIPTION_RULES:
				if marker in description_text:
					rule_matches.append((document_type, confidence, f"description contains '{marker}'"))
			for marker, document_type, confidence in cls._URL_RULES:
				if marker in url_text:
					rule_matches.append((document_type, confidence, f"url contains '{marker}'"))
			for marker, document_type, confidence in cls._CONTENT_RULES:
				if marker in content_text:
					rule_matches.append((document_type, confidence, f"content contains '{marker}'"))
		except Exception:
			return ClassificationResult(document_type="other", confidence=ClassificationConfidence.LOW, matched_rules=["fallback"], evidence=["classification exception handled"])

		if rule_matches:
			ordered = sorted(rule_matches, key=lambda item: (item[1].value != "HIGH", item[1].value != "MEDIUM", item[1].value != "LOW"))
			selected = ordered[0]
			document_type = selected[0]
			confidence = selected[1]
			rule_names = [match[2] for match in ordered if match[0] == document_type]
			if not rule_names:
				rule_names = [selected[2]]
			return ClassificationResult(
				document_type=document_type,
				confidence=confidence,
				matched_rules=rule_names,
				evidence=[selected[2]],
			)

		return ClassificationResult(
			document_type="other",
			confidence=ClassificationConfidence.LOW,
			matched_rules=["no-strong-match"],
			evidence=["document does not contain strong classification markers"],
		)


def classify_document(document: Document) -> ClassificationResult:
	return DocumentClassifier.classify(document)


__all__ = [
	"ClassificationConfidence",
	"ClassificationResult",
	"DocumentClassifier",
	"DOCUMENT_TYPES",
	"classify_document",
]
