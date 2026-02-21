"""Vector store for semantic search using sqlite-vec."""

import hashlib
import json
from dataclasses import dataclass

from .database import Database, get_database
from crewclaw.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Search result with score."""

    id: int
    content: str
    file_path: str | None
    metadata: dict | None
    score: float
    chunk_index: int | None


class VectorStore:
    """Vector store for semantic search."""

    def __init__(self, db: Database | None = None):
        """Initialize vector store.

        Args:
            db: Database instance. Uses singleton if not provided.
        """
        self._db = db
        self._embedding_dim: int | None = None

    @property
    def db(self) -> Database:
        """Get database instance."""
        if self._db is None:
            self._db = get_database()
        return self._db

    def _compute_hash(self, content: str) -> str:
        """Compute content hash for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def insert(
        self,
        content: str,
        embedding: list[float],
        file_path: str | None = None,
        metadata: dict | None = None,
        chunk_index: int = 0,
    ) -> int:
        """Insert content with embedding into vector store.

        Args:
            content: Text content.
            embedding: Vector embedding.
            file_path: Source file path.
            metadata: Additional metadata.
            chunk_index: Index of chunk in source file.

        Returns:
            Inserted row ID.
        """
        conn = self.db.connection
        content_hash = self._compute_hash(content)

        # Check for duplicates
        existing = conn.execute(
            "SELECT id FROM vectors WHERE content_hash = ?", (content_hash,)
        ).fetchone()

        if existing:
            logger.debug("Duplicate content found, skipping insert")
            return existing["id"]

        # Insert vector
        cursor = conn.execute(
            """INSERT INTO vectors 
               (content, embedding, metadata, file_path, chunk_index, content_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                content,
                json.dumps(embedding),
                json.dumps(metadata) if metadata else None,
                file_path,
                chunk_index,
                content_hash,
            ),
        )
        conn.commit()

        logger.debug(f"Inserted vector with id {cursor.lastrowid}")
        return cursor.lastrowid

    def search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        file_path: str | None = None,
    ) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_embedding: Query vector.
            limit: Maximum results.
            file_path: Optional file path to filter by.

        Returns:
            List of search results.
        """
        conn = self.db.connection

        # Build query
        if file_path:
            where_clause = "WHERE file_path = ?"
            params = (file_path, query_embedding, limit)
        else:
            where_clause = ""
            params = (query_embedding, limit)

        try:
            # Try vec similarity search
            cursor = conn.execute(
                f"""SELECT id, content, file_path, metadata, chunk_index,
                           distance
                    FROM vectors
                    {where_clause}
                    ORDER BY distance
                    LIMIT ?""",
                params,
            )
            rows = cursor.fetchall()

            results = []
            for row in rows:
                metadata = None
                if row["metadata"]:
                    metadata = json.loads(row["metadata"])

                results.append(
                    SearchResult(
                        id=row["id"],
                        content=row["content"],
                        file_path=row["file_path"],
                        metadata=metadata,
                        score=1.0 / (1.0 + row["distance"]),  # Convert distance to similarity
                        chunk_index=row["chunk_index"],
                    )
                )

            return results

        except Exception as e:
            logger.warning(f"Vector search failed: {e}, falling back to brute force")
            return self._brute_force_search(query_embedding, limit, file_path)

    def _brute_force_search(
        self,
        query_embedding: list[float],
        limit: int = 5,
        file_path: str | None = None,
    ) -> list[SearchResult]:
        """Brute force search when vec extension unavailable."""
        conn = self.db.connection

        # Get all vectors
        if file_path:
            rows = conn.execute(
                "SELECT * FROM vectors WHERE file_path = ?", (file_path,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM vectors").fetchall()

        results = []
        for row in rows:
            emb = json.loads(row["embedding"])
            # Cosine similarity
            dot = sum(a * b for a, b in zip(query_embedding, emb))
            norm1 = sum(a * a for a in query_embedding) ** 0.5
            norm2 = sum(a * a for a in emb) ** 0.5
            score = dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0

            metadata = None
            if row["metadata"]:
                metadata = json.loads(row["metadata"])

            results.append(
                SearchResult(
                    id=row["id"],
                    content=row["content"],
                    file_path=row["file_path"],
                    metadata=metadata,
                    score=score,
                    chunk_index=row["chunk_index"],
                )
            )

        # Sort by score and limit
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def delete(self, id: int) -> bool:
        """Delete vector by ID.

        Args:
            id: Vector ID.

        Returns:
            True if deleted.
        """
        conn = self.db.connection
        cursor = conn.execute("DELETE FROM vectors WHERE id = ?", (id,))
        conn.commit()
        return cursor.rowcount > 0

    def delete_by_file(self, file_path: str) -> int:
        """Delete all vectors for a file.

        Args:
            file_path: File path.

        Returns:
            Number of deleted vectors.
        """
        conn = self.db.connection
        cursor = conn.execute("DELETE FROM vectors WHERE file_path = ?", (file_path,))
        conn.commit()
        return cursor.rowcount

    def count(self) -> int:
        """Get total vector count."""
        conn = self.db.connection
        result = conn.execute("SELECT COUNT(*) as count FROM vectors").fetchone()
        return result["count"] if result else 0

    def get_by_hash(self, content_hash: str) -> list[dict]:
        """Get vectors by content hash.

        Args:
            content_hash: Content hash.

        Returns:
            List of matching vectors.
        """
        conn = self.db.connection
        return conn.execute(
            "SELECT * FROM vectors WHERE content_hash = ?", (content_hash,)
        ).fetchall()
