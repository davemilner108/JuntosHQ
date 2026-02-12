"""add_commitment_table

Revision ID: f8a5594ef175
Revises: bcfd19a7fddb
Create Date: 2026-02-11 12:50:15.569209

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f8a5594ef175'
down_revision: Union[str, Sequence[str], None] = 'bcfd19a7fddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "commitment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("member_id", sa.Integer(), nullable=False),
        sa.Column("cycle_week", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "NOT_STARTED",
                "IN_PROGRESS",
                "DONE",
                "PARTIAL",
                "BLOCKED",
                name="commitmentstatus",
            ),
            nullable=False,
            server_default="NOT_STARTED",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["member_id"],
            ["member.id"],
            name="fk_commitment_member_id_member",
        ),
        sa.UniqueConstraint(
            "member_id", "cycle_week", name="uq_commitment_member_week"
        ),
    )


def downgrade() -> None:
    op.drop_table("commitment")
