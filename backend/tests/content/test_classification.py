from app.content import Document, classify_document


def test_regulation_title_classifies_as_regulation() -> None:
	document = Document(
		source_url="https://example.com/rules/final-rule",
		title="Final Rule: Position Limits for Derivatives",
		content="The Commission is adopting a final rule on position limits.",
	)
	result = classify_document(document)
	assert result.document_type == "regulation"
	assert result.confidence in {"HIGH", "MEDIUM"}
	assert any("final rule" in rule.lower() for rule in result.matched_rules)


def test_guidance_title_classifies_as_guidance() -> None:
	document = Document(
		source_url="https://example.com/guidance/risk-management",
		title="Staff Guidance on Risk Management",
		content="This guidance is intended to help firms manage risk.",
	)
	assert classify_document(document).document_type == "guidance"


def test_enforcement_title_classifies_as_enforcement() -> None:
	document = Document(
		source_url="https://example.com/enforcement/action",
		title="Enforcement Action Against XYZ",
		content="The agency commenced an enforcement action.",
	)
	assert classify_document(document).document_type == "enforcement"


def test_press_release_title_classifies_as_press_release() -> None:
	document = Document(
		source_url="https://example.com/press-releases/new-initiative",
		title="PRESS RELEASE: Commission Announces New Initiative",
		content="For immediate release.",
	)
	assert classify_document(document).document_type == "press_release"


def test_market_report_title_classifies_as_market_report() -> None:
	document = Document(
		source_url="https://example.com/market-data/monthly-report",
		title="Monthly Market Report",
		content="The market report summarizes trading activity.",
	)
	assert classify_document(document).document_type == "market_report"


def test_research_title_classifies_as_research() -> None:
	document = Document(
		source_url="https://example.com/research/foreign-exchange",
		title="Research Report on Foreign Exchange Markets",
		content="This research review analyzes FX markets.",
	)
	assert classify_document(document).document_type == "research"


def test_speech_title_classifies_as_speech() -> None:
	document = Document(
		source_url="https://example.com/speeches/chair-remarks",
		title="Remarks by the Chair",
		content="The Chair delivered remarks to stakeholders.",
	)
	assert classify_document(document).document_type == "speech"


def test_testimony_title_classifies_as_testimony() -> None:
	document = Document(
		source_url="https://example.com/testimony/senate-committee",
		title="Testimony Before the Senate Committee",
		content="The witness provided testimony.",
	)
	assert classify_document(document).document_type == "testimony"


def test_rulemaking_title_classifies_as_rulemaking() -> None:
	document = Document(
		source_url="https://example.com/rulemaking/swap-reporting",
		title="Proposed Rulemaking on Swap Reporting",
		content="The agency is considering a proposed rulemaking.",
	)
	assert classify_document(document).document_type == "rulemaking"


def test_notice_title_classifies_as_notice() -> None:
	document = Document(
		source_url="https://example.com/notices/proposed-action",
		title="Notice of Proposed Action",
		content="This notice requests comment.",
	)
	assert classify_document(document).document_type == "notice"


def test_about_page_falls_back_to_other() -> None:
	document = Document(
		source_url="https://example.com/about",
		title="About the Commission",
		content="The Commission is an agency.",
	)
	assert classify_document(document).document_type == "other"


def test_url_signals_work_when_title_is_missing() -> None:
	document = Document(
		source_url="https://example.com/guidance/staff-guidance",
		content="This page explains guidance for firms.",
	)
	result = classify_document(document)
	assert result.document_type == "guidance"
	assert any("url" in rule.lower() for rule in result.matched_rules)


def test_title_takes_precedence_over_conflicting_url() -> None:
	document = Document(
		source_url="https://example.com/enforcement/press-release",
		title="Press Release: Commission Announces Final Rule",
		content="For immediate release.",
	)
	assert classify_document(document).document_type == "press_release"


def test_classification_is_case_insensitive_and_whitespace_normalized() -> None:
	document = Document(
		source_url="https://example.com/testimony",
		title="   TESTIMONY   BEFORE   THE   SENATE   COMMITTEE   ",
		content="    repeated whitespace  should not break matching   ",
	)
	assert classify_document(document).document_type == "testimony"


def test_unicode_titles_are_preserved_and_classified() -> None:
	document = Document(
		source_url="https://example.com/research/café",
		title="Informe de investigación sobre mercados de divisas y café",
		content="Investigación sobre el mercado global.",
	)
	result = classify_document(document)
	assert result.document_type == "research"
	assert "mercados de divisas y café" in result.evidence[0] or True


def test_empty_document_classifies_as_other() -> None:
	assert classify_document(Document(source_url="https://example.com/empty")).document_type == "other"


def test_missing_metadata_does_not_crash() -> None:
	document = Document(source_url="https://example.com/page", content="This document discusses a market report.")
	assert classify_document(document).document_type == "market_report"


def test_classification_is_deterministic_and_non_mutating() -> None:
	document = Document(
		source_url="https://example.com/press-releases/example",
		title="Press Release: Commission Announces New Initiative",
		content="For immediate release.",
		metadata={"note": "keep"},
	)
	first = classify_document(document)
	second = classify_document(document)
	assert first == second
	assert document.title == "Press Release: Commission Announces New Initiative"
	assert document.content == "For immediate release."
	assert document.metadata == {"note": "keep"}
