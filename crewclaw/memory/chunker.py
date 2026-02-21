"""Text chunking with syntax-aware splitting."""

import re
from dataclasses import dataclass
from typing import Any

from ..config import get_config
from ..config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    """Text chunk with metadata."""

    text: str
    index: int
    start_char: int
    end_char: int
    source_file: str | None = None


class Chunker:
    """Text chunker with syntax-aware splitting."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        syntax_aware: bool | None = None,
    ):
        """Initialize chunker.

        Args:
            chunk_size: Maximum chunk size in characters.
            chunk_overlap: Overlap between chunks.
            syntax_aware: Whether to respect syntax boundaries.
        """
        config = get_config()
        self.chunk_size = chunk_size or config.get("chunking.chunk_size", 500)
        self.chunk_overlap = chunk_overlap or config.get("chunking.chunk_overlap", 50)
        self.syntax_aware = syntax_aware or config.get("chunking.syntax_aware", True)

    def chunk_text(self, text: str, source_file: str | None = None) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Input text.
            source_file: Source file path.

        Returns:
            List of chunks.
        """
        if self.syntax_aware:
            return self._syntax_aware_chunk(text, source_file)
        return self._fixed_chunk(text, source_file)

    def _fixed_chunk(self, text: str, source_file: str | None = None) -> list[Chunk]:
        """Fixed-size chunking with overlap."""
        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.chunk_size

            # If not at end, try to break at word boundary
            if end < len(text):
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        index=index,
                        start_char=start,
                        end_char=end,
                        source_file=source_file,
                    )
                )
                index += 1

            start = end - self.chunk_overlap
            if start <= 0:
                break

        return chunks

    def _syntax_aware_chunk(self, text: str, source_file: str | None = None) -> list[Chunk]:
        """Syntax-aware chunking that respects boundaries."""
        chunks = []
        index = 0

        # Split by paragraphs first
        paragraphs = re.split(r"\n\n+", text)

        current_chunk = ""
        chunk_start = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding this paragraph exceeds chunk size
            if len(current_chunk) + len(para) + 2 > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(
                    Chunk(
                        text=current_chunk.strip(),
                        index=index,
                        start_char=chunk_start,
                        end_char=chunk_start + len(current_chunk),
                        source_file=source_file,
                    )
                )
                index += 1

                # Start new chunk with overlap
                overlap_text = (
                    current_chunk[-self.chunk_overlap :] if self.chunk_overlap > 0 else ""
                )
                current_chunk = overlap_text + para
                chunk_start = chunk_start + len(current_chunk) - len(overlap_text) - len(para)
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
                    chunk_start = text.find(para)

        # Add remaining chunk
        if current_chunk.strip():
            chunks.append(
                Chunk(
                    text=current_chunk.strip(),
                    index=index,
                    start_char=chunk_start,
                    end_char=chunk_start + len(current_chunk),
                    source_file=source_file,
                )
            )

        # Also handle code blocks specially
        code_blocks = self._extract_code_blocks(text)
        for block in code_blocks:
            chunks.extend(self._chunk_code_block(block, source_file))

        # Sort by position
        chunks.sort(key=lambda x: x.start_char)

        # Reindex
        for i, chunk in enumerate(chunks):
            chunk.index = i

        return chunks

    def _extract_code_blocks(self, text: str) -> list[dict[str, Any]]:
        """Extract code blocks from text."""
        blocks = []
        pattern = r"```(\w*)\n(.*?)```"

        for match in re.finditer(pattern, text, re.DOTALL):
            blocks.append(
                {
                    "language": match.group(1),
                    "code": match.group(2),
                    "start": match.start(),
                    "end": match.end(),
                }
            )

        return blocks

    def _chunk_code_block(
        self, block: dict[str, Any], source_file: str | None = None
    ) -> list[Chunk]:
        """Chunk a code block."""
        code = block["code"]
        lines = code.split("\n")

        chunks = []
        current = []

        for i, line in enumerate(lines):
            current.append(line)

            if len("\n".join(current)) > self.chunk_size:
                if current[:-1]:
                    chunks.append(
                        Chunk(
                            text="\n".join(current[:-1]),
                            index=0,
                            start_char=block["start"],
                            end_char=block["start"],
                            source_file=source_file,
                        )
                    )
                current = [current[-1]]

        if current:
            chunks.append(
                Chunk(
                    text="\n".join(current),
                    index=0,
                    start_char=block["start"],
                    end_char=block["end"],
                    source_file=source_file,
                )
            )

        return chunks
