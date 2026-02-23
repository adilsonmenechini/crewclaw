"""Directory listing tool."""

import json
from pathlib import Path
from typing import Any

from crewclaw.agent.tools.base import Tool


class DirectoryListTool(Tool):
    """List contents of a directory."""

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
        return "directory_list"

    @property
    def description(self) -> str:
        return "List files and directories in a given path."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current directory)",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "List subdirectories recursively",
                    "default": False,
                },
                "max_depth": {
                    "type": "integer",
                    "description": "Maximum depth for recursive listing",
                    "minimum": 1,
                    "maximum": 10,
                },
                "include_hidden": {
                    "type": "boolean",
                    "description": "Include hidden files (starting with .)",
                    "default": False,
                },
            },
            "required": ["path"],
        }

    def _validate_path(self, path: str) -> tuple[bool, str]:
        """Validate the directory path."""
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
        path = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", False)
        max_depth = kwargs.get("max_depth", 3)
        include_hidden = kwargs.get("include_hidden", False)

        is_valid, error_msg = self._validate_path(path)
        if not is_valid:
            return json.dumps({"error": error_msg})

        try:
            base = Path(path)
            results: dict[str, list] = {"directories": [], "files": []}

            def scan_dir(p: Path, depth: int = 0) -> None:
                if depth > max_depth:
                    return

                try:
                    entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name))
                except PermissionError:
                    return

                for entry in entries:
                    name = entry.name

                    # Skip hidden files unless requested
                    if not include_hidden and name.startswith("."):
                        continue

                    rel_path = entry.relative_to(base)

                    if entry.is_dir():
                        results["directories"].append(str(rel_path))
                        if recursive:
                            scan_dir(entry, depth + 1)
                    else:
                        results["files"].append(str(rel_path))

            scan_dir(base)

            return json.dumps(
                {
                    "path": str(base.resolve()),
                    "recursive": recursive,
                    "directories": results["directories"],
                    "files": results["files"],
                    "total_items": len(results["directories"]) + len(results["files"]),
                }
            )

        except Exception as e:
            return json.dumps({"error": f"Error listing directory: {str(e)}"})
