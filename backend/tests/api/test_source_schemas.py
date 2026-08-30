from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas.source import SourceCreate, SourceResponse, SourceUpdate
from app.models.source import Source


def test_source_create_applies_boolean_defaults() -> None:
	source = SourceCreate(
		name="CFTC",
		url="https://www.cftc.gov/",
		categories=["forex", "markets", "risk", "regulation"],
		trust_level="primary",
		license="government",
	)

	assert source.crawl_allowed is False
	assert source.active is True


@pytest.mark.parametrize(
	"data",
	[
		{
			"url": "https://www.cftc.gov/",
			"categories": ["forex"],
			"trust_level": "primary",
			"license": "government",
		},
		{
			"name": "CFTC",
			"categories": ["forex"],
			"trust_level": "primary",
			"license": "government",
		},
		{
			"name": "CFTC",
			"url": "https://www.cftc.gov/",
			"categories": "forex",
			"trust_level": "primary",
			"license": "government",
		},
	],
)
def test_source_create_rejects_invalid_data(data: dict[str, object]) -> None:
	with pytest.raises(ValidationError):
		SourceCreate.model_validate(data)


def test_source_update_allows_partial_data() -> None:
	source = SourceUpdate(active=False)

	assert source.active is False
	assert source.name is None


def test_source_response_serializes_orm_object() -> None:
	now = datetime.now(timezone.utc)
	database_source = Source(
		id=1,
		name="CFTC",
		url="https://www.cftc.gov/",
		categories=["forex", "markets", "risk", "regulation"],
		trust_level="primary",
		license="government",
		crawl_allowed=False,
		active=True,
		created_at=now,
		updated_at=now,
	)

	source = SourceResponse.model_validate(database_source)

	assert source.id == 1
	assert source.categories == ["forex", "markets", "risk", "regulation"]
	assert source.created_at == now