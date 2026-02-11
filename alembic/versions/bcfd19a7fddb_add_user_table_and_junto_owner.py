"""add_user_table_and_junto_owner

Revision ID: bcfd19a7fddb
Revises:
Create Date: 2026-02-10 17:45:42.423451

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bcfd19a7fddb"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create user table first (junto references it via owner_id)
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("avatar_url", sa.String(length=2048), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_id", name="uq_user_provider"),
    )

    # 2. Create junto table
    op.create_table(
        "junto",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["user.id"], name="fk_junto_owner_id_user"
        ),
    )

    # 3. Create member table
    op.create_table(
        "member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=100), nullable=True),
        sa.Column("junto_id", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["junto_id"], ["junto.id"], name="fk_member_junto_id_junto"
        ),
    )


def downgrade() -> None:
    op.drop_table("member")
    op.drop_table("junto")
    op.drop_table("user")
