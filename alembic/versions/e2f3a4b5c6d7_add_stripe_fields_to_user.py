"""add_stripe_fields_to_user

Revision ID: e2f3a4b5c6d7
Revises: d1e2f3a4b5c6
Create Date: 2026-03-03 22:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_user_stripe_customer_id", "user", ["stripe_customer_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_user_stripe_customer_id", "user", type_="unique")
    op.drop_column("user", "stripe_subscription_id")
    op.drop_column("user", "stripe_customer_id")
