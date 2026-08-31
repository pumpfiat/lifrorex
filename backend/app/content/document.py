from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExtractionStatus(str, Enum):
	PENDING = "pending"
	SUCCESS = "success"
	FAILED = "failed"
	UNSUPPORTED = "unsupported"


class Document(BaseModel):
	model_config = ConfigDict(extra="forbid")

	source_id: int | None = None
	source_url: str
	canonical_url: str | None = None
	title: str | None = None
	description: str | None = None
	author: str | None = None
	published_at: datetime | None = None
	modified_at: datetime | None = None
	content: str = ""
	content_type: str | None = None
	http_status: int | None = None
	extraction_status: ExtractionStatus = ExtractionStatus.PENDING
	metadata: dict[str, Any] = Field(default_factory=dict)

	@field_validator("source_url", "canonical_url")
	@classmethod
	def _validate_url(cls, value: str | None) -> str | None:
		if value is None:
			return None
		candidate = value.strip()
		if not candidate:
			raise ValueError("URL must not be empty")
		parsed = urlsplit(candidate)
		if parsed.scheme not in {"http", "https"} or not parsed.netloc:
			raise ValueError("URL must be an absolute HTTP(S) URL")
		return candidate

	@field_validator("source_id")
	@classmethod
	def _validate_source_id(cls, value: int | None) -> int | None:
		if value is None:
			return None
		if value < 1:
			raise ValueError("source_id must be positive")
		return value

	@field_validator("content_type")
	@classmethod
	def _validate_content_type(cls, value: str | None) -> str | None:
		if value is None:
			return None
		candidate = value.strip()
		if not candidate:
			raise ValueError("content_type must not be empty")
		return candidate

	@field_validator("title", "description", "author")
	@classmethod
	def _validate_title(cls, value: str | None) -> str | None:
		if value is None:
			return None
		candidate = value.strip()
		return candidate or None

	@field_validator("content")
	@classmethod
	def _validate_content(cls, value: str) -> str:
		return value or ""

	@field_validator("http_status")
	@classmethod
	def _validate_http_status(cls, value: int | None) -> int | None:
		if value is None:
			return None
		if value < 100 or value > 599:
			raise ValueError("http_status must be a valid HTTP status code")
		return value

	@field_validator("metadata")
	@classmethod
	def _validate_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
		if value is None:
			return {}
		return dict(value)
