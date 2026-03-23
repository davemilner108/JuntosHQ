"""add_coupon_gating

Revision ID: f0a1b2c3d4e5
Revises: e2f3a4b5c6d7
Create Date: 2026-03-19 21:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Add signup_verified to user table only if the column doesn't already exist.
    # A previous (now-removed) migration may have created it, so use IF NOT EXISTS
    # to keep this migration idempotent.
    if "user" in inspector.get_table_names():
        existing_columns = [c["name"] for c in inspector.get_columns("user")]
        if "signup_verified" not in existing_columns:
            op.add_column(
                "user",
                sa.Column(
                    "signup_verified",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.false(),
                ),
            )
    else:
        op.add_column(
            "user",
            sa.Column(
                "signup_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    # Create the signup_coupon table only if it doesn't already exist.
    if "signup_coupon" not in inspector.get_table_names():
        op.create_table(
            "signup_coupon",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(length=32), nullable=False),
            sa.Column("created_by_user_id", sa.Integer(), nullable=True),
            sa.Column("used_by_user_id", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"]),
            sa.ForeignKeyConstraint(["used_by_user_id"], ["user.id"]),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("code"),
        )


def downgrade() -> None:
    op.drop_table("signup_coupon")
    op.drop_column("user", "signup_verified")
