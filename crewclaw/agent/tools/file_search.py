"""File search tool using glob patterns."""

import json
from pathlib import Path
from typing import Any

from crewclaw.agent.tools.base import Tool


class FileSearchTool(Tool):
    """Search for files using glob patterns."""

    def __init__(
        self,
        restrict_to_workspace: bool | None = None,
        workspace: Path | None = None,
    ):
        import os

        if restrict_to_workspace is None:
            restrict_to_workspace = (
                str(os.environ.get("RESTRICT_TO_WORKSPACE", "true")).lower() == "true"
            )

        self.restrict_to_workspace = restrict_to_workspace
        if workspace is None:
            workspace = Path(os.environ.get("CREWCLAW_WORKSPACE", os.getcwd()))
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "file_search"

    @property
    def description(self) -> str:
        return "Find files matching a glob pattern (e.g., '**/*.py', 'src/**/*.ts')"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Glob pattern (e.g., '**/*.py')"},
                "path": {
                    "type": "string",
                    "description": "Base directory to search from (default: current directory)",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results",
                    "minimum": 1,
                    "maximum": 1000,
                    "default": 100,
                },
            },
            "required": ["pattern"],
        }

    def _validate_path(self, path: str) -> tuple[bool, str]:
        """Validate the search path."""
        try:
            p = Path(path).resolve()

            if self.restrict_to_workspace and self.workspace:
                workspace = self.workspace.resolve()
                try:
                    p.relative_to(workspace)
                except ValueError:
                    import os

                    cwd = Path(os.getcwd()).resolve()
                    if not (p == cwd or cwd in p.parents):
                        return False, f"Path '{path}' is outside allowed workspace"

            if not p.is_dir():
                return False, f"Path is not a directory: {path}"

            return True, ""
        except Exception as e:
            return False, str(e)

    async def execute(self, **kwargs: Any) -> str:
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        max_results = kwargs.get("max_results", 100)

        if not pattern:
            return json.dumps({"error": "Missing required parameter: pattern"})

        is_valid, error_msg = self._validate_path(path)
        if not is_valid:
            return json.dumps({"error": error_msg})

        try:
            base = Path(path)
            matches = list(base.glob(pattern))

            # Sort by modification time (newest first)
            matches.sort(key=lambda x: x.stat().st_mtime, reverse=True)

            # Limit results
            total = len(matches)
            matches = matches[:max_results]

            return json.dumps(
                {
                    "pattern": pattern,
                    "base_path": str(base.resolve()),
                    "total_matches": total,
                    "returned": len(matches),
                    "files": [str(m.relative_to(base)) for m in matches],
                }
            )

        except Exception as e:
            return json.dumps({"error": f"Error searching files: {str(e)}"})
