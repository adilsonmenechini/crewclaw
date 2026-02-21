"""File read tool with path restrictions."""

import json
from pathlib import Path
from typing import Any

from crewclaw.tools.base import Tool


class FileReadTool(Tool):
    """Read contents of a file with optional restrictions."""

    def __init__(
        self,
        max_size: int = 1_000_000,
        allowed_extensions: list[str] | None = None,
        restrict_to_workspace: bool | None = None,
        workspace: Path | None = None,
    ):
        import os
        self.max_size = max_size
        self.allowed_extensions = allowed_extensions
        
        # Default de restrição Global
        if restrict_to_workspace is None:
            restrict_to_workspace = str(os.environ.get("RESTRICT_TO_WORKSPACE", "true")).lower() == "true"
        
        self.restrict_to_workspace = restrict_to_workspace
        if workspace is None:
            workspace = Path(os.environ.get("CREWCLAW_WORKSPACE", os.getcwd()))
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "file_read"

    @property
    def description(self) -> str:
        return "Read the contents of a file. Returns error if file is too large or restricted."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to read"},
                "offset": {
                    "type": "integer",
                    "description": "Line number to start reading from (1-indexed)",
                    "minimum": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of lines to read",
                    "minimum": 1,
                },
            },
            "required": ["path"],
        }

    def _validate_path(self, path: str) -> tuple[bool, str]:
        """Validate the file path."""
        try:
            p = Path(path).resolve()

            # Check extension
            if self.allowed_extensions:
                if p.suffix not in self.allowed_extensions:
                    return (
                        False,
                        f"Extension '{p.suffix}' not allowed. Allowed: {self.allowed_extensions}",
                    )

            # Check workspace restriction
            if self.restrict_to_workspace and self.workspace:
                workspace = self.workspace.resolve()
                try:
                    p.relative_to(workspace)
                except ValueError:
                    # Check if at least under cwd
                    import os

                    cwd = Path(os.getcwd()).resolve()
                    if not (p == cwd or cwd in p.parents):
                        return False, f"Path '{path}' is outside allowed workspace"

            return True, ""
        except Exception as e:
            return False, str(e)

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        offset = kwargs.get("offset", 1)
        limit = kwargs.get("limit")

        if not path:
            return json.dumps({"error": "Missing required parameter: path"})

        is_valid, error_msg = self._validate_path(path)
        if not is_valid:
            return json.dumps({"error": error_msg})

        try:
            p = Path(path)

            # Check size
            size = p.stat().st_size
            if size > self.max_size:
                return json.dumps(
                    {
                        "error": f"File too large: {size} bytes (max: {self.max_size})",
                        "path": str(p),
                        "size": size,
                    }
                )

            # Read file
            lines = p.read_text(encoding="utf-8").splitlines()

            # Apply offset and limit
            start = max(0, offset - 1)
            end = len(lines) if limit is None else start + limit
            selected = lines[start:end]

            truncated = end < len(lines)

            return json.dumps(
                {
                    "path": str(p),
                    "total_lines": len(lines),
                    "offset": offset,
                    "limit": limit,
                    "truncated": truncated,
                    "content": "\n".join(selected),
                }
            )

        except FileNotFoundError:
            return json.dumps({"error": f"File not found: {path}"})
        except PermissionError:
            return json.dumps({"error": f"Permission denied: {path}"})
        except Exception as e:
            return json.dumps({"error": f"Error reading file: {str(e)}"})
