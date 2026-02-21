"""File write tool with path restrictions."""

import json
from pathlib import Path
from typing import Any

from crewclaw.tools.base import Tool


class FileWriteTool(Tool):
    """Write contents to a file with path restrictions."""

    def __init__(
        self,
        allowed_extensions: list[str] | None = None,
        restrict_to_workspace: bool | None = None,
        workspace: Path | None = None,
    ):
        import os
        self.allowed_extensions = allowed_extensions
        
        if restrict_to_workspace is None:
            restrict_to_workspace = str(os.environ.get("RESTRICT_TO_WORKSPACE", "true")).lower() == "true"
            
        self.restrict_to_workspace = restrict_to_workspace
        if workspace is None:
            workspace = Path(os.environ.get("CREWCLAW_WORKSPACE", os.getcwd()))
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "file_write"

    @property
    def description(self) -> str:
        return "Write content to a file. Creates parent directories if needed."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file to write"},
                "content": {"type": "string", "description": "Content to write to the file"},
                "append": {
                    "type": "boolean",
                    "description": "Append to file instead of overwriting",
                    "default": False,
                },
            },
            "required": ["path", "content"],
        }

    def _validate_path(self, path: str) -> tuple[bool, str]:
        """Validate the file path for writing."""
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
                    import os

                    cwd = Path(os.getcwd()).resolve()
                    if not (p == cwd or cwd in p.parents):
                        return False, f"Path '{path}' is outside allowed workspace"

            return True, ""
        except Exception as e:
            return False, str(e)

    async def execute(self, **kwargs: Any) -> str:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        append = kwargs.get("append", False)

        if not path:
            return json.dumps({"error": "Missing required parameter: path"})
        if content is None:
            return json.dumps({"error": "Missing required parameter: content"})

        is_valid, error_msg = self._validate_path(path)
        if not is_valid:
            return json.dumps({"error": error_msg})

        try:
            p = Path(path)

            # Create parent directories
            p.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)

            return json.dumps(
                {
                    "path": str(p),
                    "action": "appended" if append else "written",
                    "bytes": len(content.encode("utf-8")),
                }
            )

        except PermissionError:
            return json.dumps({"error": f"Permission denied: {path}"})
        except Exception as e:
            return json.dumps({"error": f"Error writing file: {str(e)}"})
