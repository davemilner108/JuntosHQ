"""add_subscription_tier_to_user

Revision ID: d1e2f3a4b5c6
Revises: b7c8d9e0f1a2
Create Date: 2026-03-03 20:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create the PostgreSQL enum type first (SQLite doesn't use native enums)
    conn = op.get_bind()
    dialect = conn.dialect.name

    if dialect == "postgresql":
        op.execute(
            "CREATE TYPE subscriptiontier AS ENUM ('free', 'standard', 'expanded')"
        )
        op.add_column(
            "user",
            sa.Column(
                "subscription_tier",
                sa.Enum("free", "standard", "expanded", name="subscriptiontier"),
                nullable=False,
                server_default="free",
            ),
        )
    else:
        # SQLite — store as VARCHAR
        op.add_column(
            "user",
            sa.Column(
                "subscription_tier",
                sa.String(length=20),
                nullable=False,
                server_default="free",
            ),
        )


def downgrade() -> None:
    op.drop_column("user", "subscription_tier")

    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("DROP TYPE subscriptiontier")
