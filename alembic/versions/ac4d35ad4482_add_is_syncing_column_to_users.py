"""add_is_syncing_column_to_users

Revision ID: ac4d35ad4482
Revises: 8cac8cc339e3
Create Date: 2026-01-15 16:00:46.397345

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac4d35ad4482'
down_revision: Union[str, Sequence[str], None] = '8cac8cc339e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('isSyncing', sa.Boolean(), nullable=False, server_default='false'))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'isSyncing')
