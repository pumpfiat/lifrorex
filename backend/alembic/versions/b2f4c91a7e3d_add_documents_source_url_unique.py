"""add unique constraint on documents(source_id, source_url)

Revision ID: b2f4c91a7e3d
Revises: a1ee10b838e2
Create Date: 2026-08-31 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2f4c91a7e3d'
down_revision: Union[str, Sequence[str], None] = 'a1ee10b838e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        'uq_documents_source_id_source_url', 'documents', ['source_id', 'source_url']
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_documents_source_id_source_url', 'documents', type_='unique')
