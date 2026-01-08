"""consolidate rolodex to aliases only

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-08 14:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6g7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop old tables and recreate aliases with composite PK."""
    # Drop old aliases table
    op.drop_index("ix_aliases_context", table_name="aliases")
    op.drop_index("ix_aliases_platform_target", table_name="aliases")
    op.drop_table("aliases")

    # Drop rolodex tables
    op.drop_index("ix_rolodex_channels_name", table_name="rolodex_channels")
    op.drop_table("rolodex_channels")
    op.drop_index("ix_rolodex_users_email", table_name="rolodex_users")
    op.drop_index("ix_rolodex_users_username", table_name="rolodex_users")
    op.drop_table("rolodex_users")

    # Create new aliases table with composite PK
    op.create_table(
        "aliases",
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("context", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("alias", "context", "target_type"),
    )
    op.create_index(
        "ix_aliases_platform_target",
        "aliases",
        ["platform", "target_id"],
    )
    op.create_index(
        "ix_aliases_context",
        "aliases",
        ["context"],
    )


def downgrade() -> None:
    """Restore old table structure."""
    # Drop new aliases table
    op.drop_index("ix_aliases_context", table_name="aliases")
    op.drop_index("ix_aliases_platform_target", table_name="aliases")
    op.drop_table("aliases")

    # Restore rolodex_users
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

    # Restore rolodex_channels
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

    # Restore old aliases table
    op.create_table(
        "aliases",
        sa.Column("alias", sa.String(), nullable=False),
        sa.Column("platform", sa.String(), nullable=False),
        sa.Column("target_id", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("context", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("alias"),
    )
    op.create_index(
        "ix_aliases_platform_target",
        "aliases",
        ["platform", "target_id"],
    )
    op.create_index(
        "ix_aliases_context",
        "aliases",
        ["context"],
    )
