"""
SQLAlchemy models for slack-clacks configuration database.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Context(Base):
    __tablename__ = "contexts"

    name: Mapped[str] = mapped_column(String, primary_key=True)
    access_token: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    workspace_id: Mapped[str] = mapped_column(String, nullable=False)


class CurrentContext(Base):
    __tablename__ = "current_context"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime, primary_key=True, default=datetime.utcnow
    )
    context_name: Mapped[str] = mapped_column(
        String, ForeignKey("contexts.name", ondelete="CASCADE"), nullable=False
    )
