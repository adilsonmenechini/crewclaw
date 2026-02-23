"""Logging infrastructure for CrewClaw."""

import logging
import logging.handlers
from pathlib import Path

from ..config import get_config


def setup_logging(name: str | None = None, level_override: str | None = None) -> logging.Logger:
    """Set up logging for CrewClaw.

    Args:
        name: Optional logger name. Defaults to 'crewclaw'.

    Returns:
        Configured logger instance.
    """
    config = get_config()
    logger = logging.getLogger(name or "crewclaw")

    if logger.handlers:
        return logger

    log_format = config.get(
        "logging.format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_file = config.get("logging.file")

    config_level = config.get("logging.level", "INFO").upper()
    console_level = (level_override or config_level).upper()
    file_level = config_level

    # Set main logger to DEBUG to allow all handlers to filter independently
    logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, console_level))
    console.setFormatter(logging.Formatter(log_format))
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
        )
        file_handler.setLevel(getattr(logging, file_level))
        file_handler.setFormatter(logging.Formatter(log_format))
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
