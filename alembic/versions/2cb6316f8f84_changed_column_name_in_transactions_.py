"""changed column name in transactions table

Revision ID: 2cb6316f8f84
Revises: ada78171bc44
Create Date: 2026-01-29 11:55:58.543406

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2cb6316f8f84'
down_revision: Union[str, Sequence[str], None] = 'ada78171bc44'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'transactions',
        'emailSender',
        new_column_name='email_sender'
    )
    op.alter_column(
        'transactions',
        'emailId',
        new_column_name='email_id'
    )
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'transactions',
        'email_sender',
        new_column_name='emailSender'
    )
    op.alter_column(
        'transactions',
        'email_id',
        new_column_name='emailId'
    )
    pass
