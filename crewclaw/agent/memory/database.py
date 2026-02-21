"""SQLite database initialization with vec extension."""

import sqlite3
from pathlib import Path
from typing import Any

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger

logger = get_logger(__name__)


class Database:
    """SQLite database manager with vec extension support."""

    def __init__(self, db_path: str | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database. Defaults to config value.
        """
        config = get_config()
        self.db_path = db_path or config.get("project.database_path", "./workspace/memory/crewclaw.db")
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> sqlite3.Connection:
        """Connect to database and enable vec extension.

        Returns:
            SQLite connection.
        """
        if self._conn is not None:
            return self._conn

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

        # Enable vec extension
        try:
            self._conn.execute("SELECT load_extension('vec0')")
            logger.info("Loaded vec0 extension")
        except sqlite3.OperationalError:
            try:
                self._conn.execute("SELECT load_extension('vec')")
                logger.info("Loaded vec extension")
            except sqlite3.OperationalError as e:
                logger.warning(f"Could not load vec extension: {e}")

        # Initialize schema
        self._init_schema()

        return self._conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._conn

        # Create vectors table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding BLOB NOT NULL,
                metadata TEXT,
                file_path TEXT,
                chunk_index INTEGER,
                content_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create FTS5 table for full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS vectors_fts USING fts5(
                content,
                file_path,
                content='vectors',
                content_rowid='id'
            )
        """)

        # Triggers to keep FTS in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS vectors_ai AFTER INSERT ON vectors BEGIN
                INSERT INTO vectors_fts(rowid, content, file_path)
                VALUES (new.id, new.content, new.file_path);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS vectors_ad AFTER DELETE ON vectors BEGIN
                INSERT INTO vectors_fts(vectors_fts, rowid, content, file_path)
                VALUES ('delete', old.id, old.content, old.file_path);
            END
        """)

        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS vectors_au AFTER UPDATE ON vectors BEGIN
                INSERT INTO vectors_fts(vectors_fts, rowid, content, file_path)
                VALUES ('delete', old.id, old.content, old.file_path);
                INSERT INTO vectors_fts(rowid, content, file_path)
                VALUES (new.id, new.content, new.file_path);
            END
        """)

        # Create indexes
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectors_file 
            ON vectors(file_path)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectors_hash 
            ON vectors(content_hash)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectors_updated 
            ON vectors(updated_at)
        """)

        conn.commit()
        logger.info("Database schema initialized")

    @property
    def connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            return self.connect()
        return self._conn

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "Database":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()


# Singleton instance
_db: Database | None = None


def get_database() -> Database:
    """Get singleton database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
