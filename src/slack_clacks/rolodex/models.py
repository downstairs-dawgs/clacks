"""
SQLAlchemy models for rolodex.
"""

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from slack_clacks.configuration.models import Base


class Alias(Base):
    """
    Platform-agnostic aliases for users and channels.
    Unique per (alias, context, target_type).
    """

    __tablename__ = "aliases"

    alias: Mapped[str] = mapped_column(String, primary_key=True)
    context: Mapped[str] = mapped_column(
        String, ForeignKey("contexts.name", ondelete="CASCADE"), primary_key=True
    )
    target_type: Mapped[str] = mapped_column(String, primary_key=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    target_id: Mapped[str] = mapped_column(String, nullable=False)

    __table_args__ = (
        Index("ix_aliases_platform_target", "platform", "target_id"),
        Index("ix_aliases_context", "context"),
    )
