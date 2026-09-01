"""add knowledge fingerprint

Revision ID: f5b9d3e7a014
Revises: e4f8a2c6b901
Create Date: 2026-09-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.knowledge.deduplication import knowledge_fingerprint


revision: str = "f5b9d3e7a014"
down_revision: Union[str, Sequence[str], None] = "e4f8a2c6b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
	"""Add the fingerprint used for deterministic duplicate protection."""
	op.add_column("knowledge", sa.Column("fingerprint", sa.String(length=64), nullable=True))
	connection = op.get_bind()
	records = connection.execute(sa.text("SELECT id, content FROM knowledge")).mappings()
	fingerprints: dict[str, int] = {}
	for record in records:
		fingerprint = knowledge_fingerprint(record["content"])
		if fingerprint in fingerprints:
			raise RuntimeError(
				"Cannot apply knowledge fingerprint migration with existing normalized duplicates"
			)
		fingerprints[fingerprint] = record["id"]
		connection.execute(
			sa.text("UPDATE knowledge SET fingerprint = :fingerprint WHERE id = :id"),
			{"fingerprint": fingerprint, "id": record["id"]},
		)
	op.alter_column("knowledge", "fingerprint", nullable=False)
	op.create_index("ix_knowledge_fingerprint", "knowledge", ["fingerprint"], unique=True)


def downgrade() -> None:
	"""Remove deterministic duplicate protection."""
	op.drop_index("ix_knowledge_fingerprint", table_name="knowledge")
	op.drop_column("knowledge", "fingerprint")