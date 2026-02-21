"""Error handling infrastructure for CrewClaw."""

import traceback
from typing import Any, Callable, TypeVar

from .logging import get_logger

logger = get_logger(__name__)


class CrewClawError(Exception):
    """Base exception for CrewClaw errors."""

    pass


class ConfigurationError(CrewClawError):
    """Configuration-related errors."""

    pass


class MemoryError(CrewClawError):
    """Memory operation errors."""

    pass


class VectorStoreError(CrewClawError):
    """Vector store errors."""

    pass


class AgentError(CrewClawError):
    """Agent-related errors."""

    pass


class ToolExecutionError(CrewClawError):
    """Tool execution errors."""

    pass


T = TypeVar("T")


def handle_errors(
    default_return: Any = None,
    reraise: bool = False,
    log_traceback: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator for consistent error handling.

    Args:
        default_return: Value to return on error.
        reraise: Whether to reraise the exception after handling.
        log_traceback: Whether to log the full traceback.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except CrewClawError:
                raise
            except Exception as e:
                if log_traceback:
                    logger.error(f"Error in {func.__name__}: {e}")
                    logger.debug(traceback.format_exc())
                if reraise:
                    raise
                return default_return  # type: ignore

        return wrapper  # type: ignore

    return decorator


def safe_execute(func: Callable[..., T], *args: Any, default: Any = None, **kwargs: Any) -> T:
    """Safely execute a function with error handling.

    Args:
        func: Function to execute.
        *args: Positional arguments.
        default: Default value on error.
        **kwargs: Keyword arguments.

    Returns:
        Function result or default on error.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing {func.__name__}: {e}")
        logger.debug(traceback.format_exc())
        return default
