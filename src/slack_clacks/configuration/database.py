"""
Database initialization and management utilities.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from alembic import command
from alembic.config import Config
from platformdirs import user_config_dir
from sqlalchemy import Connection, create_engine
from sqlalchemy.orm import Session, sessionmaker

from slack_clacks.configuration.models import Context, CurrentContext


def get_config_dir(config_dir: str | Path | None = None) -> Path:
    """Get the clacks configuration directory path."""
    if config_dir is None:
        config_dir = Path(user_config_dir("slack-clacks"))
    else:
        config_dir = Path(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_db_path(config_dir: str | Path | None = None, as_url: bool = False) -> str:
    """Get the path to the SQLite database file."""
    if isinstance(config_dir, str) and (
        config_dir == ":memory:" or config_dir.startswith("file::memory:")
    ):
        db_path = config_dir
    else:
        db_path = str(get_config_dir(config_dir) / "config.sqlite")

    if as_url:
        return f"sqlite:///{db_path}"
    return db_path


def get_engine(config_dir: str | Path | None = None):
    """Create and return a SQLAlchemy engine for the config database."""
    from sqlalchemy import event

    db_url = get_db_path(config_dir=config_dir, as_url=True)
    engine = create_engine(db_url, echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@contextmanager
def get_session(
    config_dir: str | Path | None = None,
) -> Generator[Session, None, None]:
    """
    Get a database session.

    Usage:
        with get_session() as session:
            # Use session
            pass
    """
    engine = get_engine(config_dir=config_dir)
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


def run_migrations(connection: Connection) -> None:
    """
    Run Alembic migrations programmatically to upgrade the database to the
    latest version.
    """
    alembic_cfg = Config()

    config_module_dir = Path(__file__).parent
    alembic_dir = config_module_dir.parent / "alembic"

    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    alembic_cfg.attributes["connection"] = connection

    command.upgrade(alembic_cfg, "head")


def ensure_db_updated(config_dir: str | Path | None = None) -> None:
    """
    Ensure the database is initialized and up-to-date.
    Runs migrations to create or upgrade the database schema.
    """
    engine = get_engine(config_dir=config_dir)
    with engine.connect() as connection:
        run_migrations(connection)


def add_context(
    session: Session, name: str, access_token: str, user_id: str, workspace_id: str
) -> Context:
    """Add a new context to the database."""
    context = Context(
        name=name,
        access_token=access_token,
        user_id=user_id,
        workspace_id=workspace_id,
    )
    session.add(context)
    session.flush()
    return context


def update_context(
    session: Session, name: str, access_token: str, user_id: str, workspace_id: str
) -> Context:
    """Update an existing context in the database."""
    context = session.query(Context).filter(Context.name == name).first()
    if context is None:
        raise ValueError(f"Context '{name}' does not exist")

    context.access_token = access_token
    context.user_id = user_id
    context.workspace_id = workspace_id
    session.flush()
    return context


def get_context(session: Session, name: str) -> Context | None:
    """Get a context by name."""
    return session.query(Context).filter(Context.name == name).first()


def set_current_context(session: Session, context_name: str) -> CurrentContext:
    """Set the current context by adding an entry to current_context history."""
    from datetime import UTC, datetime

    current_context = CurrentContext(
        timestamp=datetime.now(UTC), context_name=context_name
    )
    session.add(current_context)
    session.flush()
    return current_context
