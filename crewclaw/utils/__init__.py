"""CrewClaw Utils — Transversal utilities for logging, errors, and text."""

from .logging import setup_logging, get_logger
from .errors import (
    CrewClawError,
    ConfigurationError,
    MemoryError,
    VectorStoreError,
    AgentError,
    ToolExecutionError,
    handle_errors,
    safe_execute,
)
from .text import truncate, slugify, sanitize_filename, extract_code_blocks, word_count

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    # Errors
    "CrewClawError",
    "ConfigurationError",
    "MemoryError",
    "VectorStoreError",
    "AgentError",
    "ToolExecutionError",
    "handle_errors",
    "safe_execute",
    # Text helpers
    "truncate",
    "slugify",
    "sanitize_filename",
    "extract_code_blocks",
    "word_count",
]
