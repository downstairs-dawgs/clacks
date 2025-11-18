"""
Database initialization and management utilities.
"""

import os
from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from platformdirs import user_config_dir
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from slack_clacks.configuration.models import Base


def get_config_dir(config_dir: str | Path | None = None) -> Path:
    """Get the clacks configuration directory path."""
    if config_dir is None:
        config_dir = Path(user_config_dir("slack-clacks"))
    else:
        config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    return get_config_dir() / "config.sqlite"


def get_engine():
    """Create and return a SQLAlchemy engine for the config database."""
    db_path = get_db_path()
    db_url = f"sqlite:///{db_path}"
    return create_engine(db_url, echo=False)


def get_session() -> Generator[Session, None, None]:
    """
    Get a database session.

    Usage:
        with get_session() as session:
            # Use session
            pass
    """
    engine = get_engine()
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    This should only be used for initial setup or testing.
    In production, use run_migrations() instead.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)


def run_migrations() -> None:
    """
    Run Alembic migrations programmatically to upgrade the database to the latest version.
    """
    db_path = get_db_path()
    db_url = f"sqlite:///{db_path}"

    alembic_cfg = Config()

    config_module_dir = Path(__file__).parent
    alembic_dir = config_module_dir.parent / "alembic"

    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    command.upgrade(alembic_cfg, "head")


def ensure_db_initialized() -> None:
    """
    Ensure the database is initialized and up-to-date.
    Creates the database if it doesn't exist, then runs migrations.
    """
    db_path = get_db_path()

    if not db_path.exists():
        init_db()

    run_migrations()
