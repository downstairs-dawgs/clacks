"""add app_type to contexts

Revision ID: 6713eb6c63d1
Revises: 17063f7d3880
Create Date: 2025-11-18 21:18:22.923110

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6713eb6c63d1"
down_revision: Union[str, Sequence[str], None] = "17063f7d3880"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "contexts",
        sa.Column("app_type", sa.String(), nullable=False, server_default="clacks"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("contexts", "app_type")
