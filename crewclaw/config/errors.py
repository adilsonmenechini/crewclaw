"""Backward compatibility — Error handling moved to crewclaw.utils.errors."""

# Re-export everything from the new canonical location
from ..utils.errors import (  # noqa: F401
    CrewClawError,
    ConfigurationError,
    MemoryError,
    VectorStoreError,
    AgentError,
    ToolExecutionError,
    handle_errors,
    safe_execute,
)

__all__ = [
    "CrewClawError",
    "ConfigurationError",
    "MemoryError",
    "VectorStoreError",
    "AgentError",
    "ToolExecutionError",
    "handle_errors",
    "safe_execute",
]
