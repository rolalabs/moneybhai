"""add_last_synced_at_column_to_users

Revision ID: 9336f4c59b9c
Revises: ac4d35ad4482
Create Date: 2026-01-16 00:12:33.099194

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9336f4c59b9c'
down_revision: Union[str, Sequence[str], None] = 'ac4d35ad4482'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('lastSyncedAt', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'lastSyncedAt')
