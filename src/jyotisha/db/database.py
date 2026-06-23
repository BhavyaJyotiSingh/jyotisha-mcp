"""
Database initialization and connection management (SQLite for personal use).
"""

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path

DB_PATH = os.getenv("JYOTISHA_DB_PATH", "jyotisha.db")

def get_db_path() -> str:
    """Get absolute path to SQLite DB, ensuring directory exists."""
    path = Path(DB_PATH)
    if not path.is_absolute():
        # Relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        path = project_root / "db" / DB_PATH
    
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)

@contextmanager
def get_db():
    """Context manager for SQLite database connection."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize database schema if it doesn't exist."""
    schema_path = Path(__file__).parent / "schema.sql"
    
    if not schema_path.exists():
        # Fallback if schema file missing
        print("Warning: schema.sql not found.")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = f.read()

    with get_db() as conn:
        conn.executescript(schema)
        conn.commit()
