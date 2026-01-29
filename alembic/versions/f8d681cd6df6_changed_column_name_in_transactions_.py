"""changed column name in transactions table2

Revision ID: f8d681cd6df6
Revises: 2cb6316f8f84
Create Date: 2026-01-29 12:46:03.402898

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8d681cd6df6'
down_revision: Union[str, Sequence[str], None] = '2cb6316f8f84'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'transactions',
        'userId',
        new_column_name='user_id'
    )
    op.alter_column(
        'transactions',
        'accountId',
        new_column_name='account_id'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'transactions',
        'user_id',
        new_column_name='userId'
    )
    op.alter_column(
        'transactions',
        'account_id',
        new_column_name='accountId'
    )
