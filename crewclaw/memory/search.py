"""Hybrid search combining FTS5 and vector search."""

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .database import get_database
from .vectorstore import VectorStore, SearchResult
from .embedder import create_embedder, Embedder
from ..config import get_config
from ..config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class HybridSearchResult:
    """Hybrid search result with combined scoring."""

    id: int
    content: str
    file_path: str | None
    metadata: dict | None
    score: float
    chunk_index: int | None
    fts_score: float = 0.0
    vector_score: float = 0.0


class HybridSearch:
    """Hybrid search combining FTS5 and vector similarity."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        embedder: Embedder | None = None,
    ):
        """Initialize hybrid search.

        Args:
            vector_store: Vector store instance.
            embedder: Embedder instance.
        """
        config = get_config()
        self.vector_store = vector_store or VectorStore()
        self.embedder = embedder or create_embedder()

        self.fts_enabled = config.get("search.fts5_enabled", True)
        self.vector_enabled = config.get("search.vector_enabled", True)
        self.hybrid_rerank = config.get("search.hybrid_rerank", True)
        self.default_limit = config.get("search.default_limit", 5)
        self.recency_weight = config.get("search.recency_weight", 0.3)

    def search(
        self,
        query: str,
        limit: int | None = None,
        file_path: str | None = None,
    ) -> list[HybridSearchResult]:
        """Search using hybrid approach.

        Args:
            query: Search query.
            limit: Maximum results.
            file_path: Optional file path filter.

        Returns:
            List of hybrid search results.
        """
        limit = limit or self.default_limit

        fts_results = []
        vector_results = []

        # FTS5 search
        if self.fts_enabled:
            fts_results = self._fts_search(query, limit * 2, file_path)
            logger.debug(f"FTS5 found {len(fts_results)} results")

        # Vector search
        if self.vector_enabled:
            try:
                query_embedding = self.embedder.embed(query)
                vector_results = self.vector_store.search(query_embedding, limit * 2, file_path)
                logger.debug(f"Vector search found {len(vector_results)} results")
            except Exception as e:
                logger.warning(f"Vector search failed: {e}")

        # Combine results
        return self._combine_results(fts_results, vector_results, limit)

    def _fts_search(
        self,
        query: str,
        limit: int,
        file_path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Perform FTS5 search.

        Args:
            query: Search query.
            limit: Maximum results.
            file_path: Optional file filter.

        Returns:
            List of FTS results.
        """
        db = get_database()
        conn = db.connection

        # Build query
        if file_path:
            sql = """
                SELECT v.id, v.content, v.file_path, v.metadata, 
                       v.chunk_index, v.updated_at,
                       bm25(vectors_fts) as score
                FROM vectors_fts
                JOIN vectors v ON vectors_fts.rowid = v.id
                WHERE vectors_fts MATCH ?
                  AND v.file_path = ?
                ORDER BY score
                LIMIT ?
            """
            params = (query, file_path, limit)
        else:
            sql = """
                SELECT v.id, v.content, v.file_path, v.metadata,
                       v.chunk_index, v.updated_at,
                       bm25(vectors_fts) as score
                FROM vectors_fts
                JOIN vectors v ON vectors_fts.rowid = v.id
                WHERE vectors_fts MATCH ?
                ORDER BY score
                LIMIT ?
            """
            params = (query, limit)

        try:
            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                import json

                metadata = json.loads(row["metadata"]) if row["metadata"] else None

                # Normalize score (bm25 is negative, lower is better)
                fts_score = 1.0 / (1.0 + abs(row["score"]))

                results.append(
                    {
                        "id": row["id"],
                        "content": row["content"],
                        "file_path": row["file_path"],
                        "metadata": metadata,
                        "chunk_index": row["chunk_index"],
                        "score": fts_score,
                        "updated_at": row["updated_at"],
                    }
                )
            return results
        except Exception as e:
            logger.warning(f"FTS search failed: {e}")
            return []

    def _combine_results(
        self,
        fts_results: list[dict[str, Any]],
        vector_results: list[SearchResult],
        limit: int,
    ) -> list[HybridSearchResult]:
        """Combine and rerank results from both searches.

        Args:
            fts_results: FTS5 search results.
            vector_results: Vector search results.
            limit: Maximum results.

        Returns:
            Combined and reranked results.
        """
        # Deduplicate by content hash
        seen: dict[str, HybridSearchResult] = {}

        # Add FTS results
        for result in fts_results:
            content_hash = hashlib.sha256(result["content"].encode()).hexdigest()[:16]

            if content_hash not in seen:
                seen[content_hash] = HybridSearchResult(
                    id=result["id"],
                    content=result["content"],
                    file_path=result["file_path"],
                    metadata=result["metadata"],
                    score=result["score"],
                    chunk_index=result.get("chunk_index"),
                    fts_score=result["score"],
                    vector_score=0.0,
                )
            else:
                # Update FTS score
                seen[content_hash].fts_score = result["score"]

        # Add vector results
        for result in vector_results:
            content_hash = hashlib.sha256(result.content.encode()).hexdigest()[:16]

            if content_hash not in seen:
                seen[content_hash] = HybridSearchResult(
                    id=result.id,
                    content=result.content,
                    file_path=result.file_path,
                    metadata=result.metadata,
                    score=result.score,
                    chunk_index=result.chunk_index,
                    fts_score=0.0,
                    vector_score=result.score,
                )
            else:
                # Update vector score
                seen[content_hash].vector_score = result.score

        # Combine scores
        results = list(seen.values())

        for result in results:
            if self.hybrid_rerank:
                # Weighted combination
                fts_w = 0.5
                vector_w = 0.5
                result.score = fts_w * result.fts_score + vector_w * result.vector_score

            # Apply recency weighting
            if result.metadata and "updated_at" in result.metadata:
                try:
                    updated = datetime.fromisoformat(result.metadata["updated_at"])
                    age_days = (datetime.now() - updated).days
                    recency = 0.5 ** (age_days / 30)  # Half-life of 30 days
                    result.score = (
                        result.score * (1 - self.recency_weight) + recency * self.recency_weight
                    )
                except (ValueError, TypeError):
                    pass

        # Sort by combined score
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]
