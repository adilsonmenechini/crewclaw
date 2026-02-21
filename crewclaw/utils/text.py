"""Text utility helpers for CrewClaw."""

import re
import unicodedata


def truncate(text: str, max_length: int = 200, suffix: str = "...") -> str:
    """Truncate text to a maximum length.

    Args:
        text: Input text.
        max_length: Maximum length in characters.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """Convert text to a URL/filename-safe slug.

    Args:
        text: Input text.

    Returns:
        Slug string (lowercase, hyphens, no special chars).
    """
    # Normalize unicode
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    # Lowercase and replace spaces/underscores
    text = text.lower()
    text = re.sub(r"[\s_]+", "-", text)
    # Remove non-alphanumeric except hyphens
    text = re.sub(r"[^a-z0-9\-]", "", text)
    # Collapse multiple hyphens
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Sanitize a string so it is safe to use as a filename.

    Args:
        name: Desired filename (without extension).
        max_length: Maximum filename length.

    Returns:
        Safe filename string.
    """
    # Replace path separators and null bytes
    name = re.sub(r'[/\\:\*\?"<>|\x00]', "_", name)
    # Collapse whitespace
    name = re.sub(r"\s+", "_", name.strip())
    return name[:max_length]


def extract_code_blocks(text: str) -> list[dict]:
    """Extract fenced code blocks from markdown text.

    Args:
        text: Markdown text.

    Returns:
        List of dicts with 'language' and 'code' keys.
    """
    pattern = r"```(\w*)\n(.*?)```"
    blocks = []
    for match in re.finditer(pattern, text, re.DOTALL):
        blocks.append(
            {
                "language": match.group(1),
                "code": match.group(2).strip(),
            }
        )
    return blocks


def word_count(text: str) -> int:
    """Count words in text.

    Args:
        text: Input text.

    Returns:
        Word count.
    """
    return len(text.split())
