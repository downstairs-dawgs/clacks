"""add aliases table

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create aliases table."""
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


def downgrade() -> None:
    """Drop aliases table."""
    op.drop_index("ix_aliases_context", table_name="aliases")
    op.drop_index("ix_aliases_platform_target", table_name="aliases")
    op.drop_table("aliases")
