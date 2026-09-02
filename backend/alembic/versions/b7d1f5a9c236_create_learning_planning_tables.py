"""create learning planning tables

Revision ID: b7d1f5a9c236
Revises: a6c0e4f8b125
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b7d1f5a9c236"
down_revision: Union[str, Sequence[str], None] = "a6c0e4f8b125"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


content_difficulty = postgresql.ENUM(
	"beginner", "intermediate", "advanced", name="contentdifficulty", create_type=False
)
content_status = postgresql.ENUM(
	"draft", "review", "published", "archived", name="contentstatus", create_type=False
)
content_type = postgresql.ENUM(
	"concept", "glossary", "lesson", "question", name="contenttype", create_type=False
)


def upgrade() -> None:
	"""Create persisted learning objectives and ordered content plans."""
	progression = sa.Enum("introduce", "understand", "recognize", "apply", "decide", name="learningprogression")
	op.create_table(
		"learning_objectives",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("title", sa.String(), nullable=False),
		sa.Column("description", sa.Text(), nullable=False),
		sa.Column("difficulty", content_difficulty, nullable=False),
		sa.Column("progression", progression, nullable=False),
		sa.Column("status", content_status, nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_table(
		"learning_objective_knowledge",
		sa.Column("objective_id", sa.Integer(), nullable=False),
		sa.Column("knowledge_id", sa.Integer(), nullable=False),
		sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("objective_id", "knowledge_id"),
	)
	op.create_table(
		"learning_objective_prerequisite",
		sa.Column("objective_id", sa.Integer(), nullable=False),
		sa.Column("prerequisite_id", sa.Integer(), nullable=False),
		sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["prerequisite_id"], ["learning_objectives.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("objective_id", "prerequisite_id"),
	)
	op.create_table(
		"content_plans",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("objective_id", sa.Integer(), nullable=False),
		sa.Column("content_type", content_type, nullable=False),
		sa.Column("sequence", sa.Integer(), nullable=False),
		sa.Column("difficulty", content_difficulty, nullable=False),
		sa.Column("progression", sa.Enum("introduce", "understand", "recognize", "apply", "decide", name="learningprogression", create_type=False), nullable=False),
		sa.ForeignKeyConstraint(["objective_id"], ["learning_objectives.id"], ondelete="CASCADE"),
		sa.PrimaryKeyConstraint("id"),
		sa.UniqueConstraint("objective_id", "sequence", name="uq_content_plans_objective_sequence"),
	)


def downgrade() -> None:
	"""Remove the learning planning domain."""
	op.drop_table("content_plans")
	op.drop_table("learning_objective_prerequisite")
	op.drop_table("learning_objective_knowledge")
	op.drop_table("learning_objectives")
	op.execute("DROP TYPE learningprogression")