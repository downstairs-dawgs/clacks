"""add rolodex tables

Revision ID: a1b2c3d4e5f6
Revises: 6713eb6c63d1
Create Date: 2026-01-07 15:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "6713eb6c63d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create rolodex tables."""
    op.create_table(
        "rolodex_users",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column("real_name", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "workspace_id"),
    )
    op.create_index(
        "ix_rolodex_users_username",
        "rolodex_users",
        ["workspace_id", "username"],
    )
    op.create_index(
        "ix_rolodex_users_email",
        "rolodex_users",
        ["workspace_id", "email"],
    )

    op.create_table(
        "rolodex_channels",
        sa.Column("channel_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("channel_name", sa.String(), nullable=True),
        sa.Column("is_private", sa.Boolean(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("channel_id", "workspace_id"),
    )
    op.create_index(
        "ix_rolodex_channels_name",
        "rolodex_channels",
        ["workspace_id", "channel_name"],
    )


def downgrade() -> None:
    """Drop rolodex tables."""
    op.drop_index("ix_rolodex_channels_name", table_name="rolodex_channels")
    op.drop_table("rolodex_channels")
    op.drop_index("ix_rolodex_users_email", table_name="rolodex_users")
    op.drop_index("ix_rolodex_users_username", table_name="rolodex_users")
    op.drop_table("rolodex_users")
