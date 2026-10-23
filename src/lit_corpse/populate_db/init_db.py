import sqlite3

from pathlib import Path
from ..logger import get_logger


logger = get_logger() # initialize logger for this module


DB_PATH = Path("data/poetry.db")
DB_SCRIPT_PATH = Path("src/lit_corpse/populate_db/init_db.sql")


def get_db_connection(db_path: Path = DB_PATH, is_init: bool = False) -> sqlite3.Connection:
    """Return a connection to the SQLite database."""
    if not db_path.exists():
        if is_init:
            logger.info(f"Database '{db_path}' does not exist. Creating new database.")
        else:
            logger.error(f"Database '{db_path}' does not exist. Please initialize it first.")
            raise FileNotFoundError(f"Database '{db_path}' does not exist. Please initialize it first.")
    
    return sqlite3.connect(db_path)


def initialize_database(db_path: Path = DB_PATH, init_script_path: Path = DB_SCRIPT_PATH) -> None:
    """Initialize the SQLite database and create the necessary table and indexes."""

    if db_path.exists():
        logger.debug(f"Database '{db_path}' already exists. Deleting for reinitialization.")
        db_path.unlink()  # Remove existing database file  

    if not init_script_path.exists():
        logger.error(f"Initialization script '{init_script_path}' not found. Cannot initialize database.")
        raise FileNotFoundError(f"Initialization script '{init_script_path}' not found.")

    with get_db_connection(db_path, is_init=True) as conn:
        cursor = conn.cursor()
        cursor.executescript(init_script_path.read_text())
        conn.commit()

