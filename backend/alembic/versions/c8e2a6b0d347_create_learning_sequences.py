"""create learning sequences

Revision ID: c8e2a6b0d347
Revises: b7d1f5a9c236
Create Date: 2026-09-02 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "c8e2a6b0d347"
down_revision: Union[str, Sequence[str], None] = "b7d1f5a9c236"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


content_difficulty = postgresql.ENUM(
	"beginner", "intermediate", "advanced", name="contentdifficulty", create_type=False
)
content_status = postgresql.ENUM(
	"draft", "review", "published", "archived", name="contentstatus", create_type=False
)


def upgrade() -> None:
	"""Create ordered Learning Sequence storage."""
	op.create_table(
		"learning_sequences",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("title", sa.String(), nullable=False),
		sa.Column("description", sa.Text(), nullable=False),
		sa.Column("status", content_status, nullable=False),
		sa.Column("difficulty", content_difficulty, nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_table(
		"learning_sequence_items",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("sequence_id", sa.Integer(), nullable=False),
		sa.Column("objective_id", sa.Integer(), nullable=False),
		sa.Column("position", sa.Integer(), nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.ForeignKeyConstraint(["sequence_id"], ["learning_sequences.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("sequence_id", "objective_id", name="uq_learning_sequence_objective"),
		sa.UniqueConstraint("sequence_id", "position", name="uq_learning_sequence_position"),
	)


def downgrade() -> None:
	"""Remove Learning Sequence storage."""
	op.drop_table("learning_sequence_items")
	op.drop_table("learning_sequences")