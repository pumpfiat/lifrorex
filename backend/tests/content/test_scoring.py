from app.content import Document, DocumentScorer, score_document


def test_high_quality_high_relevance_regulatory_document() -> None:
	document = Document(
		source_url="https://example.com/rules/final-rule",
		canonical_url="https://example.com/rules/final-rule",
		title="Final Rule on Foreign Exchange Derivatives Risk",
		description="Commission final rule addressing risk management and reporting for foreign exchange derivatives.",
		author="Division",
		content=(
			"The Commission is adopting a final rule on foreign exchange derivatives risk. "
			"The rule addresses reporting, risk management, and market oversight for derivatives. "
			"This document sets clear regulatory expectations for firms operating in foreign exchange markets."
		),
	)
	result = score_document(document)
	assert 0.0 <= result.quality <= 1.0
	assert 0.0 <= result.relevance <= 1.0
	assert result.quality > 0.7
	assert result.relevance > 0.7


def test_high_quality_low_relevance_document() -> None:
	document = Document(
		source_url="https://example.com/about/facilities",
		title="Office Building Accessibility Guidelines",
		description="Guidance for building access and facility operations.",
		content="The office building guidelines explain accessibility standards for entrances, elevators, restrooms, and visitor routes. "
		"The document provides operational guidance for facility managers and staff.",
	)
	result = score_document(document)
	assert result.quality > 0.6
	assert result.relevance < 0.4


def test_low_quality_high_relevance_document() -> None:
	document = Document(
		source_url="https://example.com/foreign-exchange/risk",
		title="Foreign Exchange Risk",
		content="Forex.",
	)
	result = score_document(document)
	assert result.quality < 0.5
	assert result.relevance > 0.4


def test_low_quality_low_relevance_document() -> None:
	document = Document(source_url="https://example.com/page", title="Page", content="")
	result = score_document(document)
	assert result.quality < 0.3
	assert result.relevance < 0.3


def test_empty_document_is_safe() -> None:
	document = Document(source_url="https://example.com/empty")
	result = score_document(document)
	assert 0.0 <= result.quality <= 1.0
	assert 0.0 <= result.relevance <= 1.0
	assert result.quality == 0.0
	assert result.relevance == 0.0


def test_metadata_rich_document_increases_quality_without_perfection() -> None:
	document = Document(
		source_url="https://example.com/report",
		canonical_url="https://example.com/report",
		title="Quarterly Market Summary",
		description="Quarterly market summary for regulated firms.",
		author="Research Desk",
		published_at="2026-01-15T00:00:00Z",
		content="This is a concise summary.",
	)
	result = score_document(document)
	assert result.quality > 0.4
	assert result.quality < 0.9


def test_content_rich_document_with_little_metadata_can_still_score_high() -> None:
	document = Document(
		source_url="https://example.com/analysis",
		title="Analysis",
		content="The foreign exchange market experienced volatility as central bank interest rate decisions changed liquidity conditions. "
		"The report reviews derivatives exposure, swap pricing, and risk management for market participants. "
		"It also discusses monetary policy and financial regulation in the context of trading flows.",
	)
	result = score_document(document)
	assert result.quality > 0.6
	assert result.relevance > 0.7


def test_boilerplate_heavy_document_does_not_get_high_quality() -> None:
	document = Document(
		source_url="https://example.com/site",
		title="Home",
		content="Home About Contact Jobs Legal Terms Privacy Information Business Market News Report Careers Support Contact Us "
		"Information Business Market News Report Careers Support Contact Us Information Business Market News Report.",
	)
	result = score_document(document)
	assert result.quality < 0.5
	assert result.relevance < 0.5


def test_relevance_keywords_are_weighted_and_capped() -> None:
	document = Document(
		source_url="https://example.com/tags",
		title="Forex Forex Forex Forex Forex",
		content="forex forex forex forex forex foreign exchange market risk derivatives swap compliance.",
	)
	result = score_document(document)
	assert 0.0 <= result.relevance <= 1.0
	assert result.relevance > 0.4
	assert result.relevance < 1.0


def test_case_and_whitespace_are_normalized() -> None:
	document = Document(
		source_url="https://example.com/forex",
		title="  FOREX   AND   DERIVATIVES   ",
		content="   foreign    exchange    risk    management   ",
	)
	result = score_document(document)
	assert result.relevance > 0.6


def test_unicode_is_preserved_and_scored() -> None:
	document = Document(
		source_url="https://example.com/es/mercados",
		title="Informe sobre mercados de divisas y riesgo financiero",
		content="Este informe analiza divisas, riesgo, y política monetaria en los mercados financieros.",
	)
	result = score_document(document)
	assert result.relevance > 0.5
	assert "divisas" in document.title.lower()


def test_scoring_is_deterministic_and_non_mutating() -> None:
	document = Document(
		source_url="https://example.com/report",
		title="Foreign Exchange Market Risk Report",
		description="Analysis of market risk and derivatives disclosures.",
		content="This report reviews foreign exchange market risk, derivatives, and liquidity conditions.",
		metadata={"source": "internal"},
	)
	first = score_document(document)
	second = score_document(document)
	assert first == second
	assert document.title == "Foreign Exchange Market Risk Report"
	assert document.description == "Analysis of market risk and derivatives disclosures."
	assert document.metadata == {"source": "internal"}


def test_result_has_explainable_evidence() -> None:
	document = Document(
		source_url="https://example.com/markets/risk",
		title="Market Risk and Foreign Exchange Overview",
		content="The report covers foreign exchange, derivatives, and system risk.",
	)
	result = score_document(document)
	assert result.quality_evidence
	assert result.relevance_evidence
