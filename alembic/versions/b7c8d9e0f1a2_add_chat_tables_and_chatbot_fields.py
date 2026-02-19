"""add_chat_tables_and_chatbot_fields

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add chatbot fields to user, and create chat_session / chat_message tables."""
    op.add_column(
        "user",
        sa.Column(
            "chatbot_msgs_used", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "chatbot_addon", sa.Boolean(), nullable=False, server_default="false"
        ),
    )

    op.create_table(
        "chat_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("junto_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["user.id"], name="fk_chat_session_user_id_user"
        ),
        sa.ForeignKeyConstraint(
            ["junto_id"], ["junto.id"], name="fk_chat_session_junto_id_junto"
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chat_message",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=10), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["chat_session.id"],
            name="fk_chat_message_session_id_chat_session",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("chat_message")
    op.drop_table("chat_session")
    op.drop_column("user", "chatbot_addon")
    op.drop_column("user", "chatbot_msgs_used")
