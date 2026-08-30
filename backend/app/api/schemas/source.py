from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SourceCreate(BaseModel):
	name: NonEmptyString
	url: NonEmptyString
	categories: list[str]
	trust_level: str
	license: str
	crawl_allowed: bool = False
	active: bool = True


class SourceUpdate(BaseModel):
	name: NonEmptyString = None
	url: NonEmptyString = None
	categories: list[str] = None
	trust_level: str = None
	license: str = None
	crawl_allowed: bool = None
	active: bool = None


class SourceResponse(BaseModel):
	model_config = ConfigDict(from_attributes=True)

	id: int
	name: str
	url: str
	categories: list[str]
	trust_level: str
	license: str
	crawl_allowed: bool
	active: bool
	created_at: datetime
	updated_at: datetime