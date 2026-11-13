import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from ..logger import get_logger

logger = get_logger()

DEFAULT_DB_PATH = Path("poetry.db")
DB_SCRIPT_PATH = Path(__file__).parent / "init_db.sql"


def resolve_db_path(db_path: Path | str | None = None) -> Path:
    """Resolve database path, checking local directory and data/ directory."""
    if db_path is not None:
        target = Path(db_path)
        if target.exists():
            return target
        # If specified as "poetry.db" and "data/poetry.db" exists, resolve to data/poetry.db
        alt_path = Path("data") / target.name
        if alt_path.exists():
            return alt_path
        return target

    # Default lookup: check poetry.db, then data/poetry.db
    if DEFAULT_DB_PATH.exists():
        return DEFAULT_DB_PATH
    data_db = Path("data/poetry.db")
    if data_db.exists():
        return data_db
    return DEFAULT_DB_PATH


@contextmanager
def get_db_connection(
    db_path: Path | str = DEFAULT_DB_PATH,
    is_init: bool = False,
) -> Generator[sqlite3.Connection, None, None]:
    """Context manager returning an active connection to the SQLite database.

    Automatically closes the database connection on exit.

    Args:
        db_path: Path to the SQLite database file.
        is_init: If True, allows creating parent directories and the db file.

    Yields:
        sqlite3.Connection: Active database connection.
    """
    path = Path(db_path)
    if not path.exists():
        if is_init:
            path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Database '{path}' does not exist. Creating new database.")
        else:
            logger.error(f"Database '{path}' does not exist. Please initialize it first.")
            raise FileNotFoundError(f"Database '{path}' does not exist. Please initialize it first.")

    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def initialize_database(
    db_path: Path | str = DEFAULT_DB_PATH,
    init_script_path: Path | str = DB_SCRIPT_PATH,
) -> None:
    """Initialize the SQLite database and create the necessary table and indexes.

    Args:
        db_path: Path to the SQLite database file.
        init_script_path: Path to SQL schema script.
    """
    path = Path(db_path)
    script_path = Path(init_script_path)

    if path.exists():
        logger.debug(f"Database '{path}' already exists. Deleting for reinitialization.")
        path.unlink()

    if not script_path.exists():
        logger.error(f"Initialization script '{script_path}' not found. Cannot initialize database.")
        raise FileNotFoundError(f"Initialization script '{script_path}' not found.")

    with get_db_connection(path, is_init=True) as conn:
        cursor = conn.cursor()
        cursor.executescript(script_path.read_text(encoding="utf-8"))
        conn.commit()
    logger.info(f"Database '{path}' initialized successfully.")
