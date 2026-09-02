"""Deterministic boundary from a Content Plan to future Content creation."""

from app.api.schemas.content_creation import ContentCreationSpec
from app.models.content import ContentType
from app.services.learning_repository import LearningRepository


_REQUIRED_FIELDS: dict[ContentType, tuple[str, ...]] = {
	ContentType.CONCEPT: ("name", "summary"),
	ContentType.GLOSSARY: ("term", "definition"),
	ContentType.LESSON: ("introduction", "sections", "key_takeaways"),
	ContentType.QUESTION: ("prompt", "answer", "explanation"),
}


class ContentPlanningError(Exception):
	"""Raised when a valid creation specification cannot be derived."""


class ContentPlanningService:
	"""Produces validated creation requirements without generating Content."""

	def __init__(self, repository: LearningRepository):
		self.repository = repository

	def create_spec_from_plan(self, content_plan_id: int) -> ContentCreationSpec:
		"""Derive one deterministic spec from an existing, grounded Content Plan."""
		plan = self.repository.get_plan(content_plan_id)
		if plan is None:
			raise ContentPlanningError(f"Content plan {content_plan_id} was not found")
		objective = self.repository.get_objective(plan.objective_id)
		if objective is None:
			raise ContentPlanningError("Content plan objective was not found")
		knowledge_ids = tuple(knowledge.id for knowledge in objective.knowledge_records)
		if not knowledge_ids:
			raise ContentPlanningError("Learning objective must reference Knowledge")
		if len(knowledge_ids) != len(set(knowledge_ids)):
			raise ContentPlanningError("Learning objective Knowledge references must be unique")

		return ContentCreationSpec(
			content_plan_id=plan.id,
			objective_id=objective.id,
			content_type=plan.content_type,
			difficulty=plan.difficulty,
			progression=plan.progression,
			sequence=plan.sequence,
			title_guidance=objective.title,
			objective_description=objective.description,
			knowledge_ids=knowledge_ids,
			required_fields=_REQUIRED_FIELDS[plan.content_type],
		)


__all__ = ["ContentPlanningError", "ContentPlanningService"]