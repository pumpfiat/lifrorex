"""create content tables

Revision ID: a6c0e4f8b125
Revises: f5b9d3e7a014
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6c0e4f8b125"
down_revision: Union[str, Sequence[str], None] = "f5b9d3e7a014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Create content and content-to-knowledge association tables."""
	content_type = sa.Enum("concept", "glossary", "lesson", "question", name="contenttype")
	content_status = sa.Enum("draft", "review", "published", "archived", name="contentstatus")
	content_difficulty = sa.Enum("beginner", "intermediate", "advanced", name="contentdifficulty")
	creation_method = sa.Enum(
		"manual", "rule_based", "llm_assisted", "llm_generated", name="contentcreationmethod"
	)
	op.create_table(
		"content",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("content_type", content_type, nullable=False),
		sa.Column("status", content_status, nullable=False),
		sa.Column("difficulty", content_difficulty, nullable=False),
		sa.Column("title", sa.String(), nullable=False),
		sa.Column("body", sa.Text(), nullable=False),
		sa.Column("payload", sa.JSON(), nullable=False),
		sa.Column("creation_method", creation_method, nullable=False),
		sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_table(
		"content_knowledge",
		sa.Column("content_id", sa.Integer(), nullable=False),
		sa.Column("knowledge_id", sa.Integer(), nullable=False),
		sa.ForeignKeyConstraint(["content_id"], ["content.id"], ondelete="CASCADE"),
		sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("content_id", "knowledge_id"),
	)


def downgrade() -> None:
	"""Remove the Content foundation tables."""
	op.drop_table("content_knowledge")
	op.drop_table("content")
	op.execute("DROP TYPE contentcreationmethod")
	op.execute("DROP TYPE contentdifficulty")
	op.execute("DROP TYPE contentstatus")
	op.execute("DROP TYPE contenttype")