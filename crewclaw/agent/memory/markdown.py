"""Markdown file handling for memory storage."""

import hashlib
from datetime import datetime
from pathlib import Path

import yaml

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger

logger = get_logger(__name__)


class MemoryFile:
    """Handler for Markdown memory files."""

    def __init__(self, file_path: str):
        """Initialize memory file.

        Args:
            file_path: Path to Markdown file.
        """
        self.file_path = Path(file_path)
        self._content: str | None = None
        self._frontmatter: dict | None = None

    @property
    def content(self) -> str:
        """Get file content."""
        if self._content is None:
            if self.file_path.exists():
                self._read()
            else:
                self._content = ""
        return self._content  # type: ignore[return-value]

    @property
    def frontmatter(self) -> dict:
        """Get YAML frontmatter."""
        if self._frontmatter is None:
            self._parse_frontmatter()
        return self._frontmatter  # type: ignore[return-value]

    def _read(self) -> None:
        """Read file and parse frontmatter."""
        with open(self.file_path) as f:
            content = f.read()

        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                self._frontmatter = yaml.safe_load(parts[1]) or {}
                self._content = parts[2].strip()
            else:
                self._content = content
        else:
            self._content = content

    def _parse_frontmatter(self) -> None:
        """Parse frontmatter from content."""
        if self._content is None:
            self._read()

        if self._frontmatter is None:
            self._frontmatter = {}

    def write(
        self,
        content: str,
        metadata: dict | None = None,
        template: str | None = None,
    ) -> None:
        """Write content to file with frontmatter.

        Args:
            content: Markdown content.
            metadata: YAML frontmatter metadata.
            template: Template name to use.
        """
        # Build frontmatter
        fm = metadata or {}
        fm.setdefault("created_at", datetime.now().isoformat())
        fm.setdefault("updated_at", datetime.now().isoformat())
        fm.setdefault("template", template)

        # Add content hash for deduplication
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        fm["content_hash"] = content_hash

        # Build file content
        frontmatter_str = yaml.dump(fm, default_flow_style=False)
        self._content = content
        self._frontmatter = fm

        # Ensure directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(self.file_path, "w") as f:
            f.write("---\n")
            f.write(frontmatter_str)
            f.write("---\n\n")
            f.write(content)

        logger.debug(f"Wrote memory file: {self.file_path}")

    def update(self, content: str) -> None:
        """Update file content, preserving frontmatter.

        Args:
            content: New content.
        """
        # Preserve existing frontmatter
        existing_fm = self.frontmatter.copy()
        existing_fm["updated_at"] = datetime.now().isoformat()

        self.write(content, existing_fm)

    def delete(self) -> bool:
        """Delete the memory file.

        Returns:
            True if deleted.
        """
        if self.file_path.exists():
            self.file_path.unlink()
            logger.debug(f"Deleted memory file: {self.file_path}")
            return True
        return False

    @property
    def content_hash(self) -> str:
        """Get content hash."""
        return hashlib.sha256(self.content.encode()).hexdigest()[:16]

    @property
    def exists(self) -> bool:
        """Check if file exists."""
        return self.file_path.exists()

    @property
    def modified_time(self) -> datetime | None:
        """Get file modification time."""
        if self.exists:
            ts = self.file_path.stat().st_mtime
            return datetime.fromtimestamp(ts)
        return None


class MemoryOrganizer:
    """Organize memory files by date and category."""

    def __init__(self, base_dir: str | None = None):
        """Initialize organizer.

        Args:
            base_dir: Base directory for memories.
        """
        config = get_config()
        self.base_dir = Path(base_dir or config.get("project.memory_dir", "./workspace/memory"))
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_path(
        self,
        date: datetime | None = None,
        category: str | None = None,
    ) -> Path:
        """Get file path for memory.

        Args:
            date: Date for memory. Defaults to today.
            category: Category folder.

        Returns:
            Full file path.
        """
        date = date or datetime.now()

        path = self.base_dir

        if category:
            path = path / category

        # Date-based organization
        path = path / str(date.year) / f"{date.month:02d}" / f"{date.day:02d}"

        path.mkdir(parents=True, exist_ok=True)

        return path

    def list_memories(
        self,
        category: str | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[MemoryFile]:
        """List memory files.

        Args:
            category: Filter by category.
            start_date: Filter by start date.
            end_date: Filter by end date.

        Returns:
            List of memory files.
        """
        memories = []

        # Walk through directory
        for file_path in self.base_dir.rglob("*.md"):
            # Skip hidden files
            if file_path.name.startswith("."):
                continue

            # Check category filter
            if category:
                if category not in file_path.parts:
                    continue

            # Check date filters
            if start_date or end_date:
                try:
                    # Extract date from path
                    parts = file_path.parts
                    year = int(parts[-3])
                    month = int(parts[-2])
                    day = int(parts[-1].replace(".md", ""))
                    file_date = datetime(year, month, day)

                    if start_date and file_date < start_date:
                        continue
                    if end_date and file_date > end_date:
                        continue
                except (ValueError, IndexError):
                    continue

            memories.append(MemoryFile(str(file_path)))

        return memories
