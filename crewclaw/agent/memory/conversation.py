"""Conversation memory with vector store and summarization."""

import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger
from crewclaw.providers.embedder import create_embedder
from .vectorstore import VectorStore
from .search import HybridSearch

logger = get_logger(__name__)


class ConversationMemory:
    """Persistent conversation memory using vector store."""

    def __init__(self, db_path: str | None = None):
        """Initialize conversation memory.

        Args:
            db_path: Path to conversation database.
        """
        config = get_config()
        self.db_path = db_path or config.get(
            "project.conversation_db", "./workspace/memory/conversations.db"
        )
        self._conn: sqlite3.Connection | None = None
        self.embedder = create_embedder()
        self.vector_store = VectorStore(db=None)  # Use default shared database
        self.hybrid_search = HybridSearch(vector_store=self.vector_store, embedder=self.embedder)

    def connect(self) -> sqlite3.Connection:
        """Connect to database."""
        if self._conn is not None:
            return self._conn

        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

        return self._conn

    def _init_schema(self) -> None:
        """Initialize conversation schema."""
        conn = self.connection  # Use property to ensure connection

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()

        self._migrate_schema()

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_conversations_session
            ON conversations(session_id)
        """)

        conn.commit()
        logger.info("Conversation memory schema initialized")

    def _migrate_schema(self) -> None:
        """Migrate schema if needed."""
        conn = self.connection  # Use property to ensure connection

        try:
            conn.execute("SELECT content_hash FROM conversations LIMIT 1")
        except sqlite3.OperationalError:
            conn.execute("ALTER TABLE conversations ADD COLUMN content_hash TEXT")
            conn.commit()
            logger.info("Migrated: added content_hash column")

    @property
    def connection(self) -> sqlite3.Connection:
        """Get database connection."""
        if self._conn is None:
            return self.connect()
        return self._conn

    def add_message(self, session_id: str, role: str, content: str) -> bool:
        """Add a message to conversation history with deduplication and compaction.

        Args:
            session_id: Session identifier.
            role: Message role (user/assistant).
            content: Message content.

        Returns:
            True if message was added, False if duplicate.
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:32]

        conn = self.connection

        existing = conn.execute(
            "SELECT id FROM conversations WHERE session_id = ? AND content_hash = ?",
            (session_id, content_hash),
        ).fetchone()

        if existing:
            logger.debug(f"Duplicate message detected: {content_hash[:8]}...")
            return False

        conn.execute(
            "INSERT INTO conversations (session_id, role, content, content_hash) VALUES (?, ?, ?, ?)",
            (session_id, role, content, content_hash),
        )
        conn.commit()

        # Optimization: Compact context if it's getting too long
        self._compact_if_needed(session_id)

        self._update_vector_for_session(session_id)

        return True

    def _compact_if_needed(self, session_id: str) -> None:
        """Check and compact session if it exceeds token threshold."""
        config = get_config()
        threshold = config.get("memory.compaction_threshold_tokens", 4000)

        messages = self.get_all_messages(session_id)
        if not messages:
            return

        # Simple token estimation: ~4 chars per token on average for English
        total_chars = sum(len(m["content"]) for m in messages)
        estimated_tokens = total_chars / 4

        if estimated_tokens > threshold:
            logger.info(f"Session {session_id} exceeds threshold ({estimated_tokens:.0f} tokens), compacting...")
            self._compact_session(session_id, messages)

    def _compact_session(self, session_id: str, messages: list[dict]) -> None:
        """Compact session by summarizing the first half of messages."""
        # Keep the last 4 messages as raw context
        keep_count = 4
        if len(messages) <= keep_count + 2:
            return

        to_summarize = messages[:-keep_count]
        text_to_summarize = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])

        try:
            # We use the feedback loop's summarization logic if available, or a simple prompt
            from crewclaw.providers.crewai import create_crewai_llm

            llm = create_crewai_llm()
            prompt = (
                f"Summarize the following part of a conversation to preserve its context "
                f"in a very concise way (under 200 words):\n\n{text_to_summarize}"
            )

            # Handle both crewai.LLM and other potential wrappers
            if hasattr(llm, "call"):
                summary = llm.call([{"role": "user", "content": prompt}])
            else:
                # Basic fallback if call() is not there
                return

            # Delete old messages
            conn = self.connection
            # Get IDs of messages to delete (all but the last keep_count)
            rows = conn.execute(
                "SELECT id FROM conversations WHERE session_id = ? ORDER BY created_at ASC LIMIT ?",
                (session_id, len(to_summarize)),
            ).fetchall()
            ids_to_delete = [row["id"] for row in rows]

            if ids_to_delete:
                placeholders = ",".join(["?"] * len(ids_to_delete))
                conn.execute(
                    f"DELETE FROM conversations WHERE id IN ({placeholders})", tuple(ids_to_delete)
                )

                # Add summary as a system message at the beginning
                conn.execute(
                    "INSERT INTO conversations (session_id, role, content) VALUES (?, ?, ?)",
                    (session_id, "system", f"[Context Summary]: {summary}"),
                )
                conn.commit()
                logger.info(f"Session {session_id} compacted successfully")

        except Exception as e:
            logger.warning(f"Context compaction failed: {e}")

    def _update_vector_for_session(self, session_id: str) -> None:
        """Update vector store for session messages and summary."""
        messages = self.get_all_messages(session_id)

        if not messages:
            return

        combined_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])

        try:
            embedding = self.embedder.embed(combined_text)
            file_path = f"conversation:{session_id}"

            self.vector_store.delete_by_file(file_path)

            self.vector_store.insert(
                content=combined_text,
                embedding=embedding,
                file_path=file_path,
                metadata={
                    "session_id": session_id,
                    "type": "conversation_session",
                    "message_count": len(messages),
                    "updated_at": datetime.now().isoformat(),
                },
            )
            logger.debug(f"Vector updated for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update vector for session {session_id}: {e}")

    def get_recent_messages(self, session_id: str, limit: int = 10) -> list[dict]:
        """Get recent messages from a session.

        Args:
            session_id: Session identifier.
            limit: Number of messages to retrieve.

        Returns:
            List of message dicts.
        """
        conn = self.connection
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM conversations
            WHERE session_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (session_id, limit),
        ).fetchall()

        # Return in chronological order
        messages = [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
        return messages

    def get_all_messages(self, session_id: str) -> list[dict]:
        """Get all messages from a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of message dicts.
        """
        conn = self.connection
        rows = conn.execute(
            """
            SELECT role, content, created_at
            FROM conversations
            WHERE session_id = ?
            ORDER BY created_at ASC
            """,
            (session_id,),
        ).fetchall()

        return [{"role": row["role"], "content": row["content"]} for row in rows]

    def get_summary(self, session_id: str) -> str | None:
        """Get conversation summary.

        Args:
            session_id: Session identifier.

        Returns:
            Summary text or None.
        """
        conn = self.connection
        row = conn.execute(
            "SELECT summary FROM conversation_summaries WHERE session_id = ?",
            (session_id,),
        ).fetchone()

        return row["summary"] if row else None

    def save_summary(self, session_id: str, summary: str) -> None:
        """Save or update conversation summary and vector embedding.

        Args:
            session_id: Session identifier.
            summary: Summary text.
        """
        conn = self.connection
        conn.execute(
            """
            INSERT INTO conversation_summaries (session_id, summary, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(session_id) DO UPDATE SET
                summary = excluded.summary,
                updated_at = CURRENT_TIMESTAMP
            """,
            (session_id, summary),
        )
        conn.commit()

        # Update vector store for semantic search
        try:
            embedding = self.embedder.embed(summary)
            # Use session_id as the file_path identifier in vector store to easily update/delete
            file_path = f"conversation:{session_id}"

            # Delete any existing vectors for this session's summary to keep it fresh
            self.vector_store.delete_by_file(file_path)

            # Combined content: summary + session info
            vector_content = f"Conversation Summary (Session {session_id}): {summary}"

            self.vector_store.insert(
                content=vector_content,
                embedding=embedding,
                file_path=file_path,
                metadata={
                    "session_id": session_id,
                    "type": "conversation_summary",
                    "updated_at": datetime.now().isoformat(),
                },
            )
            logger.debug(f"Vector embedding updated for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update vector embedding for session {session_id}: {e}")

    def get_context_for_new_session(
        self, current_session_id: str, query: str | None = None
    ) -> list[dict]:
        """Get relevant context from all previous sessions.

        Uses generic hybrid search when a query is provided, or
        falls back to recent sessions if no query.

        Args:
            current_session_id: Current session ID (to exclude).
            query: The initial user query to find semantically relevant sessions.

        Returns:
            List of relevant messages.
        """
        messages = []

        if query:
            # Semantic search to find the most relevant past conversations
            try:
                # Search using Hybrid Motor
                results = self.hybrid_search.search(query, limit=5)

                # Filter out the current session if it happens to match, and only keep summaries
                relevant_summaries = [
                    res
                    for res in results
                    if res.metadata
                    and res.metadata.get("type") == "conversation_summary"
                    and res.metadata.get("session_id") != current_session_id
                ]

                for result in relevant_summaries:
                    if result.metadata is None:
                        continue
                    session_id = result.metadata.get("session_id", "unknown")
                    score_str = f"({result.score:.2f} relevance)"
                    messages.append(
                        {
                            "role": "system",
                            "content": f"[Context from previous session {session_id} {score_str}]: {result.content}",
                        }
                    )
            except Exception as e:
                logger.warning(f"Hybrid search failed for context retrieval: {e}")

        # If no query provided or search returned empty, fallback to recent 5 chronologically
        if not messages:
            conn = self.connection
            summaries = conn.execute(
                """
                SELECT session_id, summary, updated_at
                FROM conversation_summaries
                WHERE session_id != ?
                ORDER BY updated_at DESC
                LIMIT 5
                """,
                (current_session_id,),
            ).fetchall()

            for row in summaries:
                messages.append(
                    {
                        "role": "system",
                        "content": f"[Context from recent session {row['session_id']}]: {row['summary']}",
                    }
                )

        return messages

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> "ConversationMemory":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        """Context manager exit."""
        self.close()


# Singleton instance
_conv_memory: ConversationMemory | None = None


def get_conversation_memory() -> ConversationMemory:
    """Get singleton conversation memory instance."""
    global _conv_memory
    if _conv_memory is None:
        _conv_memory = ConversationMemory()
    return _conv_memory
