"""create evidence table

Revision ID: e4f8a2c6b901
Revises: d3a1e9f4c702
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f8a2c6b901"
down_revision: Union[str, Sequence[str], None] = "d3a1e9f4c702"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema."""
	op.create_table(
		"evidence",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("knowledge_id", sa.Integer(), nullable=False),
		sa.Column("document_id", sa.Integer(), nullable=False),
		sa.Column("text", sa.Text(), nullable=False),
		sa.Column("start_offset", sa.Integer(), nullable=True),
		sa.Column("end_offset", sa.Integer(), nullable=True),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("now()"),
			nullable=False,
		),
		sa.ForeignKeyConstraint(["knowledge_id"], ["knowledge.id"], ondelete="RESTRICT"),
		sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_evidence_knowledge_id", "evidence", ["knowledge_id"], unique=False)
	op.create_index("ix_evidence_document_id", "evidence", ["document_id"], unique=False)


def downgrade() -> None:
	"""Downgrade schema."""
	op.drop_index("ix_evidence_document_id", table_name="evidence")
	op.drop_index("ix_evidence_knowledge_id", table_name="evidence")
	op.drop_table("evidence")