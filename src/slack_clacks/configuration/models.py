"""
SQLAlchemy models for slack-clacks configuration database.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Context(Base):
    __tablename__ = "contexts"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workspace_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    workspace_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
