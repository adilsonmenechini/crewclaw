"""File watcher for automatic memory re-indexing."""

import time
from pathlib import Path
from typing import Callable

from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileDeletedEvent,
)

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger

logger = get_logger(__name__)


class MemoryEventHandler(FileSystemEventHandler):
    """Handler for memory file changes."""

    def __init__(
        self,
        on_created: Callable[[str], None] | None = None,
        on_modified: Callable[[str], None] | None = None,
        on_deleted: Callable[[str], None] | None = None,
        debounce_seconds: float = 1.0,
    ):
        """Initialize handler.

        Args:
            on_created: Callback for file creation.
            on_modified: Callback for file modification.
            on_deleted: Callback for file deletion.
            debounce_seconds: Seconds to wait before processing.
        """
        self.on_created = on_created
        self.on_modified = on_modified
        self.on_deleted = on_deleted
        self.debounce_seconds = debounce_seconds

        self._last_event: dict[str, float] = {}
        self._pending: dict[str, str] = {}

    def _should_process(self, path: str) -> bool:
        """Check if event should be processed (debouncing)."""
        now = time.time()
        last_time = self._last_event.get(path, 0)

        if now - last_time < self.debounce_seconds:
            return False

        self._last_event[path] = now
        return True

    def on_created(self, event: FileCreatedEvent) -> None:
        """Handle file creation."""
        if event.is_directory:
            return

        if not self._should_process(event.src_path):
            return

        logger.info(f"File created: {event.src_path}")

        if self.on_created:
            self.on_created(event.src_path)

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Handle file modification."""
        if event.is_directory:
            return

        if not self._should_process(event.src_path):
            return

        logger.info(f"File modified: {event.src_path}")

        if self.on_modified:
            self.on_modified(event.src_path)

    def on_deleted(self, event: FileDeletedEvent) -> None:
        """Handle file deletion."""
        if event.is_directory:
            return

        logger.info(f"File deleted: {event.src_path}")

        if self.on_deleted:
            self.on_deleted(event.src_path)


class FileWatcher:
    """File system watcher for memory directory."""

    def __init__(
        self,
        watch_paths: list[str] | None = None,
        on_created: Callable[[str], None] | None = None,
        on_modified: Callable[[str], None] | None = None,
        on_deleted: Callable[[str], None] | None = None,
    ):
        """Initialize watcher.

        Args:
            watch_paths: Paths to watch.
            on_created: Callback for file creation.
            on_modified: Callback for file modification.
            on_deleted: Callback for file deletion.
        """
        config = get_config()

        self.watch_paths = watch_paths or config.get("watch.watch_paths", ["./workspace/memory"])
        debounce = config.get("watch.debounce_seconds", 1.0)

        self.handler = MemoryEventHandler(
            on_created=on_created,
            on_modified=on_modified,
            on_deleted=on_deleted,
            debounce_seconds=debounce,
        )

        self._observer: Observer | None = None

    def start(self) -> None:
        """Start watching."""
        if self._observer is not None:
            return

        self._observer = Observer()

        for path in self.watch_paths:
            watch_path = Path(path)
            if watch_path.exists():
                self._observer.schedule(self.handler, str(watch_path), recursive=True)
                logger.info(f"Watching: {watch_path}")
            else:
                logger.warning(f"Path does not exist: {watch_path}")

        self._observer.start()
        logger.info("File watcher started")

    def stop(self) -> None:
        """Stop watching."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            logger.info("File watcher stopped")

    def __enter__(self) -> "FileWatcher":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit."""
        self.stop()
