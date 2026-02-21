"""Observation memory for tool usage insights."""

from datetime import datetime

from crewclaw.config.logging import get_logger
from crewclaw.providers.embedder import create_embedder
from .vectorstore import VectorStore

logger = get_logger(__name__)

class ObservationMemory:
    """Manages long-term storage of tool execution insights."""

    def __init__(self):
        """Initialize observation memory."""
        self.embedder = create_embedder()
        self.vector_store = VectorStore(db=None)

    def save_observation(self, tool_name: str, result: str) -> None:
        """Save a tool execution insight.

        Args:
            tool_name: The name of the tool executed.
            result: The output string of the tool.
        """
        # Skip empty or very short results
        if not result or len(result.strip()) < 20:
            return

        # Skip JSON error objects
        if result.startswith("{") and '"error"' in result.lower():
            return
            
        # Truncate at 2000 chars to avoid enormous vector entries
        truncated = result
        if len(truncated) > 2000:
            truncated = truncated[:1997] + "..."

        try:
            insight_text = f"Tool '{tool_name}' observed: {truncated}"
            embedding = self.embedder.embed(insight_text)
            
            # Using current timestamp + tool_name as pseudo unique path 
            # VectorStore uses content_hash for deduplication
            file_path = f"observation:{tool_name}"
            
            self.vector_store.insert(
                content=insight_text,
                embedding=embedding,
                file_path=file_path,
                metadata={
                    "type": "tool_observation",
                    "tool": tool_name,
                    "updated_at": datetime.now().isoformat()
                }
            )
            logger.debug(f"Saved observation for tool '{tool_name}'")
        except Exception as e:
            logger.warning(f"Failed to save tool observation: {e}")

# Singleton instance
_obs_memory: ObservationMemory | None = None

def get_observation_memory() -> ObservationMemory:
    """Get singleton observation memory instance."""
    global _obs_memory
    if _obs_memory is None:
        _obs_memory = ObservationMemory()
    return _obs_memory
