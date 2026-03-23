"""merge heads

Revision ID: 61bcc47d28e3
Revises: 1386dda8d17b, f0a1b2c3d4e5
Create Date: 2026-03-23 11:56:56.479166

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '61bcc47d28e3'
down_revision: Union[str, Sequence[str], None] = ('1386dda8d17b', 'f0a1b2c3d4e5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
