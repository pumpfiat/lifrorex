"""Provider-free creators that turn approved material into validated Content."""

from typing import Any, Protocol

from app.api.schemas.content import ContentCreate
from app.api.schemas.content_creation import ContentCreationSpec
from app.models.content import ContentCreationMethod, ContentStatus


class ContentCreationError(Exception):
	"""Raised when explicit material does not satisfy a creation specification."""


class ContentCreator(Protocol):
	"""Creates validated Content contracts without persistence or external calls."""

	def create(
		self, spec: ContentCreationSpec, material: dict[str, Any]
	) -> ContentCreate:
		"""Transform approved material into a valid ContentCreate contract."""


class DeterministicContentCreator:
	"""Copies explicitly supplied material into existing typed Content contracts."""

	def create(self, spec: ContentCreationSpec, material: dict[str, Any]) -> ContentCreate:
		if not isinstance(spec, ContentCreationSpec):
			raise ContentCreationError("spec must be a ContentCreationSpec")
		if not isinstance(material, dict):
			raise ContentCreationError("material must be a dictionary")
		missing_fields = {"title", "body", *spec.required_fields}.difference(material)
		if missing_fields:
			raise ContentCreationError(
				f"material is missing required fields: {', '.join(sorted(missing_fields))}"
			)

		payload = {field_name: material[field_name] for field_name in spec.required_fields}
		for field_name in ("key_points", "simple_explanation", "example", "options", "correct_option"):
			if field_name in material:
				payload[field_name] = material[field_name]
		try:
			return ContentCreate(
				content_type=spec.content_type,
				status=ContentStatus.DRAFT,
				difficulty=spec.difficulty,
				title=material["title"],
				body=material["body"],
				payload=payload,
				creation_method=ContentCreationMethod.RULE_BASED,
				knowledge_ids=list(spec.knowledge_ids),
			)
		except ValueError as error:
			raise ContentCreationError("material does not satisfy the content contract") from error


__all__ = ["ContentCreationError", "ContentCreator", "DeterministicContentCreator"]