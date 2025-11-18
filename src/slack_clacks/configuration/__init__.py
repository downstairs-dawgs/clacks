"""
Configuration management for slack-clacks.

This module handles:
- SQLite database for storing contexts and settings
- SQLAlchemy models for Context and Settings
- Database initialization and migrations via Alembic
- CRUD operations for context management
"""

from slack_clacks.configuration.models import Context, CurrentContext
from slack_clacks.configuration.database import (
    get_db_path,
    init_db,
    run_migrations,
    get_session,
)

__all__ = [
    "Context",
    "CurrentContext",
    "get_db_path",
    "init_db",
    "run_migrations",
    "get_session",
]
