from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.api.schemas.learning_sequence import (
	LearningSequenceCreate,
	LearningSequenceItemCreate,
	LearningSequenceUpdate,
)
from app.models.content import ContentStatus
from app.models.learning import LearningObjective
from app.models.learning_sequence import LearningSequence, LearningSequenceItem


class LearningSequenceRepository:
	"""Transactional persistence for deterministic Learning Objective order."""

	def __init__(self, session: Session):
		self.session = session

	def create(self, sequence: LearningSequenceCreate) -> LearningSequence:
		return self._commit_new(LearningSequence(**sequence.model_dump()))

	def get_by_id(self, sequence_id: int) -> LearningSequence | None:
		stmt = select(LearningSequence).options(
			selectinload(LearningSequence.items).selectinload(LearningSequenceItem.objective)
		).where(LearningSequence.id == sequence_id)
		return self.session.scalars(stmt).first()

	def list(self, limit: int = 100, offset: int = 0) -> list[LearningSequence]:
		if limit <= 0:
			raise ValueError("limit must be positive")
		if offset < 0:
			raise ValueError("offset must be non-negative")
		stmt = select(LearningSequence).order_by(LearningSequence.id).limit(limit).offset(offset)
		return list(self.session.scalars(stmt).all())

	def update(self, sequence_id: int, update: LearningSequenceUpdate) -> LearningSequence | None:
		sequence = self.get_by_id(sequence_id)
		if sequence is None:
			return None
		try:
			for field_name, value in update.model_dump(exclude_unset=True).items():
				setattr(sequence, field_name, value)
			self.session.commit()
			self.session.refresh(sequence)
			return sequence
		except Exception:
			self.session.rollback()
			raise

	def archive(self, sequence_id: int) -> LearningSequence | None:
		return self.update(sequence_id, LearningSequenceUpdate(status=ContentStatus.ARCHIVED))

	def add_objective(
		self, sequence_id: int, item: LearningSequenceItemCreate
	) -> LearningSequenceItem:
		sequence = self._sequence(sequence_id)
		objective = self.session.get(LearningObjective, item.objective_id)
		if objective is None:
			raise ValueError("objective_id must reference an existing LearningObjective")
		self._validate_prerequisite_order(sequence, objective, item.position)
		return self._commit_new(
			LearningSequenceItem(sequence_id=sequence.id, objective_id=objective.id, position=item.position)
		)

	def remove_objective(self, sequence_id: int, objective_id: int) -> bool:
		item = self._item_for_objective(sequence_id, objective_id)
		if item is None:
			return False
		try:
			self.session.delete(item)
			self.session.commit()
			return True
		except Exception:
			self.session.rollback()
			raise

	def reorder_objective(
		self, sequence_id: int, objective_id: int, position: int
	) -> LearningSequenceItem | None:
		if position < 1:
			raise ValueError("position must be positive")
		sequence = self._sequence(sequence_id)
		item = self._item_for_objective(sequence_id, objective_id)
		if item is None:
			return None
		self._validate_prerequisite_order(sequence, item.objective, position, item.id)
		try:
			previous_position = item.position
			item.position = max((other.position for other in sequence.items), default=0) + 1
			self.session.flush()
			for other in sequence.items:
				if other.id != item.id and other.position == position:
					other.position = previous_position
			item.position = position
			self.session.commit()
			self.session.refresh(item)
			return item
		except IntegrityError:
			self.session.rollback()
			raise ValueError("position must be unique within a sequence") from None
		except Exception:
			self.session.rollback()
			raise

	def list_objectives(self, sequence_id: int) -> list[LearningSequenceItem]:
		self._sequence(sequence_id)
		stmt = select(LearningSequenceItem).where(
			LearningSequenceItem.sequence_id == sequence_id
		).order_by(LearningSequenceItem.position)
		return list(self.session.scalars(stmt).all())

	def _sequence(self, sequence_id: int) -> LearningSequence:
		sequence = self.get_by_id(sequence_id)
		if sequence is None:
			raise ValueError("sequence_id must reference an existing LearningSequence")
		return sequence

	def _item_for_objective(self, sequence_id: int, objective_id: int) -> LearningSequenceItem | None:
		stmt = select(LearningSequenceItem).where(
			LearningSequenceItem.sequence_id == sequence_id,
			LearningSequenceItem.objective_id == objective_id,
		)
		return self.session.scalars(stmt).first()

	def _validate_prerequisite_order(
		self,
		sequence: LearningSequence,
		objective: LearningObjective,
		position: int,
		exclude_item_id: int | None = None,
	) -> None:
		positions = {
			item.objective_id: item.position
			for item in sequence.items
			if item.id != exclude_item_id
		}
		for prerequisite in objective.prerequisites:
			prerequisite_position = positions.get(prerequisite.id)
			if prerequisite_position is None or prerequisite_position >= position:
				raise ValueError("prerequisites must appear before dependent objectives")
		for item in sequence.items:
			if item.id != exclude_item_id and objective.id in {dependency.id for dependency in item.objective.prerequisites}:
				if position >= item.position:
					raise ValueError("prerequisites must appear before dependent objectives")

	def _commit_new(self, record):
		try:
			self.session.add(record)
			self.session.commit()
			self.session.refresh(record)
			return record
		except IntegrityError:
			self.session.rollback()
			raise ValueError("duplicate objective or position within sequence") from None
		except Exception:
			self.session.rollback()
			raise


__all__ = ["LearningSequenceRepository"]