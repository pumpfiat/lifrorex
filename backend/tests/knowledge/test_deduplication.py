import pytest

from app.knowledge.deduplication import (
	knowledge_fingerprint,
	normalize_knowledge_content,
)


@pytest.mark.parametrize(
	("content", "expected"),
	[
		("hello world", "hello world"),
		(" hello   world ", "hello world"),
		("Leverage", "leverage"),
		("LEVERAGE", "leverage"),
		("Definition.", "definition"),
		("Definition!", "definition"),
		("Cafe\u0301", "café"),
	],
)
def test_normalize_knowledge_content_is_deterministic(content, expected):
	assert normalize_knowledge_content(content) == expected


@pytest.mark.parametrize("content", ["", "   "])
def test_blank_content_cannot_be_fingerprinted(content):
	with pytest.raises(ValueError):
		knowledge_fingerprint(content)


def test_equivalent_content_has_the_same_deterministic_fingerprint():
	first = knowledge_fingerprint("A pip is a unit of price movement.")
	second = knowledge_fingerprint(" A Pip Is A Unit Of Price Movement! ")

	assert first == second
	assert first == knowledge_fingerprint("A pip is a unit of price movement.")


def test_different_content_has_a_different_fingerprint():
	assert knowledge_fingerprint(
		"Leverage allows traders to control larger positions."
	) != knowledge_fingerprint("Leverage magnifies both potential gains and losses.")