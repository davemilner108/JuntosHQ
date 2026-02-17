"""add_is_public_drop_commitment_uq

Revision ID: a1b2c3d4e5f6
Revises: 693e2651098b
Create Date: 2026-02-13 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '693e2651098b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_public to junto, drop commitment unique constraint."""
    op.add_column(
        'junto',
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default='true'),
    )
    op.drop_constraint('uq_commitment_member_week', 'commitment', type_='unique')


def downgrade() -> None:
    """Remove is_public, restore commitment unique constraint."""
    op.create_unique_constraint(
        'uq_commitment_member_week', 'commitment', ['member_id', 'cycle_week']
    )
    op.drop_column('junto', 'is_public')
