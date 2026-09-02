from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.learning import (
	ContentPlanCreate,
	ContentPlanUpdate,
	LearningObjectiveCreate,
	LearningObjectiveUpdate,
)
from app.models.knowledge import Knowledge
from app.models.learning import ContentPlan, LearningObjective


class LearningRepository:
	"""Persistence for grounded objectives and their deterministic content plans."""

	def __init__(self, session: Session):
		self.session = session

	def create_objective(self, objective: LearningObjectiveCreate) -> LearningObjective:
		knowledge_records = self._knowledge_records(objective.knowledge_ids)
		prerequisites = self._objectives(objective.prerequisite_ids)
		try:
			db_objective = LearningObjective(
				**objective.model_dump(exclude={"knowledge_ids", "prerequisite_ids"}),
				knowledge_records=knowledge_records,
				prerequisites=prerequisites,
			)
			self.session.add(db_objective)
			self.session.commit()
			self.session.refresh(db_objective)
			return db_objective
		except Exception:
			self.session.rollback()
			raise

	def get_objective(self, objective_id: int) -> LearningObjective | None:
		stmt = select(LearningObjective).options(
			selectinload(LearningObjective.knowledge_records),
			selectinload(LearningObjective.prerequisites),
			selectinload(LearningObjective.plans),
		).where(LearningObjective.id == objective_id)
		return self.session.scalars(stmt).first()

	def list_objectives(self, limit: int = 100, offset: int = 0) -> list[LearningObjective]:
		if limit <= 0:
			raise ValueError("limit must be positive")
		if offset < 0:
			raise ValueError("offset must be non-negative")
		stmt = select(LearningObjective).order_by(LearningObjective.id).limit(limit).offset(offset)
		return list(self.session.scalars(stmt).all())

	def update_objective(
		self, objective_id: int, update: LearningObjectiveUpdate
	) -> LearningObjective | None:
		existing = self.get_objective(objective_id)
		if existing is None:
			return None
		changes = update.model_dump(exclude_unset=True)
		knowledge_ids = changes.pop("knowledge_ids", None)
		prerequisite_ids = changes.pop("prerequisite_ids", None)
		try:
			if knowledge_ids is not None:
				existing.knowledge_records = self._knowledge_records(knowledge_ids)
			if prerequisite_ids is not None:
				if objective_id in prerequisite_ids:
					raise ValueError("an objective cannot be its own prerequisite")
				existing.prerequisites = self._objectives(prerequisite_ids)
			for field_name, value in changes.items():
				setattr(existing, field_name, value)
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except Exception:
			self.session.rollback()
			raise

	def create_plan(self, plan: ContentPlanCreate) -> ContentPlan:
		objective = self.get_objective(plan.objective_id)
		if objective is None:
			raise ValueError("objective_id must reference an existing LearningObjective")
		try:
			db_plan = ContentPlan(**plan.model_dump())
			self.session.add(db_plan)
			self.session.commit()
			self.session.refresh(db_plan)
			return db_plan
		except IntegrityError:
			self.session.rollback()
			raise ValueError("sequence must be unique for an objective") from None

	def get_plan(self, plan_id: int) -> ContentPlan | None:
		return self.session.get(ContentPlan, plan_id)

	def list_plans(self, objective_id: int) -> list[ContentPlan]:
		stmt = select(ContentPlan).where(ContentPlan.objective_id == objective_id).order_by(ContentPlan.sequence)
		return list(self.session.scalars(stmt).all())

	def update_plan(self, plan_id: int, update: ContentPlanUpdate) -> ContentPlan | None:
		existing = self.get_plan(plan_id)
		if existing is None:
			return None
		try:
			for field_name, value in update.model_dump(exclude_unset=True).items():
				setattr(existing, field_name, value)
			self.session.commit()
			self.session.refresh(existing)
			return existing
		except IntegrityError:
			self.session.rollback()
			raise ValueError("sequence must be unique for an objective") from None

	def _knowledge_records(self, knowledge_ids: list[int]) -> list[Knowledge]:
		records = list(self.session.scalars(select(Knowledge).where(Knowledge.id.in_(knowledge_ids))).all())
		if len(records) != len(knowledge_ids):
			raise ValueError("knowledge_ids must reference existing Knowledge records")
		return records

	def _objectives(self, objective_ids: list[int]) -> list[LearningObjective]:
		records = list(self.session.scalars(select(LearningObjective).where(LearningObjective.id.in_(objective_ids))).all())
		if len(records) != len(objective_ids):
			raise ValueError("prerequisite_ids must reference existing LearningObjectives")
		return records


__all__ = ["LearningRepository"]