"""
SQLAlchemy models for rolodex tables.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from slack_clacks.configuration.models import Base


class RolodexUser(Base):
    __tablename__ = "rolodex_users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str | None] = mapped_column(String, nullable=True)
    real_name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_rolodex_users_username", "workspace_id", "username"),
        Index("ix_rolodex_users_email", "workspace_id", "email"),
    )


class RolodexChannel(Base):
    __tablename__ = "rolodex_channels"

    channel_id: Mapped[str] = mapped_column(String, primary_key=True)
    workspace_id: Mapped[str] = mapped_column(String, primary_key=True)
    channel_name: Mapped[str | None] = mapped_column(String, nullable=True)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_rolodex_channels_name", "workspace_id", "channel_name"),
    )


class Alias(Base):
    """
    Platform-agnostic aliases for users and channels.
    Aliases are globally unique and scoped to a context to prevent cross-context leaks.
    """

    __tablename__ = "aliases"

    alias: Mapped[str] = mapped_column(String, primary_key=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)  # 'slack', 'github'
    target_id: Mapped[str] = mapped_column(String, nullable=False)  # U123, C456, etc.
    target_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # 'user', 'channel'
    context: Mapped[str] = mapped_column(String, nullable=False)  # context name

    __table_args__ = (
        Index("ix_aliases_platform_target", "platform", "target_id"),
        Index("ix_aliases_context", "context"),
    )
