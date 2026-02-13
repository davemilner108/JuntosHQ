"""expand_models_and_invites

Revision ID: 693e2651098b
Revises: c44433b1879f
Create Date: 2026-02-13 10:59:34.713412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '693e2651098b'
down_revision: Union[str, Sequence[str], None] = 'c44433b1879f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create the memberstatus enum type explicitly for PostgreSQL
    memberstatus = sa.Enum(
        'INVITED', 'ACTIVE', 'INACTIVE', name='memberstatus'
    )
    memberstatus.create(op.get_bind(), checkfirst=True)

    # member_invite table
    op.create_table(
        'member_invite',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('junto_id', sa.Integer(), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('accepted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['junto_id'], ['junto.id']),
        sa.ForeignKeyConstraint(['member_id'], ['member.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )

    # Junto: add meeting_url
    op.add_column(
        'junto',
        sa.Column('meeting_url', sa.String(length=2048), nullable=True),
    )

    # Member: add new columns
    op.add_column(
        'member',
        sa.Column('user_id', sa.Integer(), nullable=True),
    )
    op.add_column(
        'member',
        sa.Column('email', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'member',
        sa.Column('occupation', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'member', sa.Column('bio', sa.Text(), nullable=True)
    )
    op.add_column(
        'member',
        sa.Column('joined_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'member',
        sa.Column(
            'status',
            memberstatus,
            nullable=False,
            server_default='ACTIVE',
        ),
    )
    op.add_column(
        'member',
        sa.Column('avatar_url', sa.String(length=2048), nullable=True),
    )
    op.create_foreign_key(
        'fk_member_user_id', 'member', 'user', ['user_id'], ['id']
    )

    # User: add new columns
    op.add_column(
        'user',
        sa.Column('user_timezone', sa.String(length=50), nullable=True),
    )
    op.add_column(
        'user', sa.Column('bio', sa.Text(), nullable=True)
    )
    op.add_column(
        'user',
        sa.Column('location', sa.String(length=255), nullable=True),
    )
    op.add_column(
        'user',
        sa.Column('last_active_at', sa.DateTime(), nullable=True),
    )
    op.add_column(
        'user', sa.Column('notification_prefs', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    # User columns
    op.drop_column('user', 'notification_prefs')
    op.drop_column('user', 'last_active_at')
    op.drop_column('user', 'location')
    op.drop_column('user', 'bio')
    op.drop_column('user', 'user_timezone')

    # Member columns
    op.drop_constraint('fk_member_user_id', 'member', type_='foreignkey')
    op.drop_column('member', 'avatar_url')
    op.drop_column('member', 'status')
    op.drop_column('member', 'joined_at')
    op.drop_column('member', 'bio')
    op.drop_column('member', 'occupation')
    op.drop_column('member', 'email')
    op.drop_column('member', 'user_id')

    # Junto columns
    op.drop_column('junto', 'meeting_url')

    # Drop member_invite table
    op.drop_table('member_invite')

    # Drop the memberstatus enum type
    sa.Enum(name='memberstatus').drop(op.get_bind(), checkfirst=True)
