"""Session manager for conversation context."""

from datetime import datetime

from crewclaw.config.logging import get_logger
from crewclaw.agent.memory.conversation import get_conversation_memory
from crewclaw.agent.memory.vectorstore import (
    VectorStore as VectorStore,
    SearchResult as SearchResult,
)
from crewclaw.agent.memory.markdown import (
    MemoryFile as MemoryFile,
    MemoryOrganizer as MemoryOrganizer,
)
from crewclaw.providers.llm import create_llm

logger = get_logger(__name__)


class SessionManager:
    """Manages conversation sessions with persistent memory."""

    def __init__(self, session_id: str | None = None):
        """Initialize session manager.

        Args:
            session_id: Optional session ID. Generates new if not provided.
        """
        self.session_id = session_id or self._generate_session_id()
        self.conversation_memory = get_conversation_memory()
        self._llm = None
        self._max_messages_before_summary = 10

    def _generate_session_id(self) -> str:
        """Generate a new session ID based on date and time."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    @property
    def llm(self):
        """Get LLM instance for summarization."""
        if self._llm is None:
            self._llm = create_llm()
        return self._llm

    def load_context(self, query: str | None = None) -> list[dict]:
        """Load conversation context for this session.

        Args:
            query: Optional current query for semantic matching.

        Returns:
            List of message dicts to prepend to conversation.
        """
        context = []

        # Get summary from this session if exists
        summary = self.conversation_memory.get_summary(self.session_id)
        if summary:
            context.append(
                {"role": "system", "content": f"[Previous conversation summary]: {summary}"}
            )

        # Get context from other sessions
        other_context = self.conversation_memory.get_context_for_new_session(
            self.session_id, query=query
        )
        context.extend(other_context)

        # Get recent messages from this session
        recent = self.conversation_memory.get_recent_messages(self.session_id, limit=5)
        context.extend(recent)

        logger.info(f"Loaded {len(context)} context messages for session {self.session_id}")
        return context

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history.

        Args:
            role: Message role (user/assistant).
            content: Message content.
        """
        self.conversation_memory.add_message(self.session_id, role, content)

        # Check if we need to summarize
        messages = self.conversation_memory.get_all_messages(self.session_id)
        if len(messages) >= self._max_messages_before_summary * 2:
            self._summarize_if_needed()

    def _summarize_if_needed(self) -> None:
        """Summarize conversation if it gets too long."""
        messages = self.conversation_memory.get_all_messages(self.session_id)

        if len(messages) < self._max_messages_before_summary:
            return

        try:
            # Create summary prompt
            conversation_text = "\n".join(
                f"{msg['role']}: {msg['content'][:200]}..."
                for msg in messages[-self._max_messages_before_summary :]
            )

            summary_prompt = f"""Summarize this conversation concisely, keeping important facts:
{conversation_text}

Provide a brief summary (2-3 sentences) capturing the key points."""

            summary = self.llm.complete([{"role": "user", "content": summary_prompt}])

            if summary:
                self.conversation_memory.save_summary(self.session_id, summary)
                logger.info(f"Saved summary for session {self.session_id}")

        except Exception as e:
            logger.warning(f"Failed to summarize conversation: {e}")

    def get_formatted_context(self) -> str:
        """Get context formatted as a string for LLM.

        Returns:
            Formatted context string.
        """
        context = self.load_context()
        if not context:
            return ""

        lines = ["Context from previous conversations:"]
        for msg in context:
            lines.append(f"- {msg['role']}: {msg['content'][:150]}...")

        return "\n".join(lines)

    def close(self) -> None:
        """Close session resources."""
        self.conversation_memory.close()


# Global session manager
_current_session: SessionManager | None = None


def get_current_session() -> SessionManager:
    """Get current session manager."""
    global _current_session
    if _current_session is None:
        _current_session = SessionManager()
    return _current_session


def set_session(session_id: str) -> SessionManager:
    """Set current session by ID.

    Args:
        session_id: Session identifier.

    Returns:
        SessionManager instance.
    """
    global _current_session
    _current_session = SessionManager(session_id)
    return _current_session


__all__ = [
    "SessionManager",
    "get_current_session",
    "set_session",
    "VectorStore",
    "SearchResult",
    "MemoryFile",
    "MemoryOrganizer",
]
