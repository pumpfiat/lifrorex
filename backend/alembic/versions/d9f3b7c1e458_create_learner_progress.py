"""create learner progress

Revision ID: d9f3b7c1e458
Revises: c8e2a6b0d347
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9f3b7c1e458"
down_revision: Union[str, Sequence[str], None] = "c8e2a6b0d347"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Create learner-specific objective progress state."""
	status = sa.Enum("not_started", "in_progress", "completed", name="learnerprogressstatus")
	op.create_table(
		"learner_objective_progress",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("learner_id", sa.Integer(), nullable=False),
		sa.Column("objective_id", sa.Integer(), nullable=False),
		sa.Column("status", status, nullable=False),
		sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("learner_id", "objective_id", name="uq_learner_objective_progress"),
	)


def downgrade() -> None:
	"""Remove learner-specific objective progress state."""
	op.drop_table("learner_objective_progress")
	op.execute("DROP TYPE learnerprogressstatus")