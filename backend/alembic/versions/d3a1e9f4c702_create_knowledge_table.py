"""create knowledge table

Revision ID: d3a1e9f4c702
Revises: b2f4c91a7e3d
Create Date: 2026-08-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d3a1e9f4c702"
down_revision: Union[str, Sequence[str], None] = "b2f4c91a7e3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Upgrade schema."""
	op.create_table(
		"knowledge",
		sa.Column("id", sa.Integer(), nullable=False),
		sa.Column("document_id", sa.Integer(), nullable=False),
		sa.Column("knowledge_type", sa.String(), nullable=False),
		sa.Column("content", sa.Text(), nullable=False),
		sa.Column("metadata", sa.JSON(), nullable=False),
		sa.Column(
			"created_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("now()"),
			nullable=False,
		),
		sa.Column(
			"updated_at",
			sa.DateTime(timezone=True),
			server_default=sa.text("now()"),
			nullable=False,
		),
		sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="RESTRICT"),
		sa.PrimaryKeyConstraint("id"),
	)
	op.create_index("ix_knowledge_document_id", "knowledge", ["document_id"], unique=False)
	op.create_index(
		"ix_knowledge_knowledge_type", "knowledge", ["knowledge_type"], unique=False
	)


def downgrade() -> None:
	"""Downgrade schema."""
	op.drop_index("ix_knowledge_knowledge_type", table_name="knowledge")
	op.drop_index("ix_knowledge_document_id", table_name="knowledge")
	op.drop_table("knowledge")