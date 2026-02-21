"""Grep tool for searching file contents."""

import json
import re
from pathlib import Path
from typing import Any

from crewclaw.agent.tools.base import Tool


class GrepTool(Tool):
    """Search for text patterns in files."""

    def __init__(
        self,
        restrict_to_workspace: bool = False,
        workspace: Path | None = None,
    ):
        self.restrict_to_workspace = restrict_to_workspace
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "grep"

    @property
    def description(self) -> str:
        return "Search for text patterns in files. Supports regex and returns matching lines."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "Search pattern (supports regex)"},
                "path": {
                    "type": "string",
                    "description": "File or directory path to search",
                },
                "case_sensitive": {
                    "type": "boolean",
                    "description": "Case sensitive search",
                    "default": True,
                },
                "whole_word": {
                    "type": "boolean",
                    "description": "Match whole word only",
                    "default": False,
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of matching lines to return",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 100,
                },
            },
            "required": ["pattern", "path"],
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

            return True, ""
        except Exception as e:
            return False, str(e)

    async def execute(self, **kwargs: Any) -> str:
        pattern = kwargs.get("pattern", "")
        path = kwargs.get("path", ".")
        case_sensitive = kwargs.get("case_sensitive", True)
        whole_word = kwargs.get("whole_word", False)
        max_results = kwargs.get("max_results", 100)

        if not pattern:
            return json.dumps({"error": "Missing required parameter: pattern"})

        is_valid, error_msg = self._validate_path(path)
        if not is_valid:
            return json.dumps({"error": error_msg})

        try:
            base_path = Path(path)

            # Build regex
            regex_pattern = pattern
            if whole_word:
                regex_pattern = r"\b" + re.escape(pattern) + r"\b"

            flags = 0 if case_sensitive else re.IGNORECASE
            regex = re.compile(regex_pattern, flags)

            # Collect files to search
            if base_path.is_file():
                files_to_search = [base_path]
            elif base_path.is_dir():
                files_to_search = [
                    f for f in base_path.rglob("*") if f.is_file() and not f.name.startswith(".")
                ]
            else:
                return json.dumps({"error": f"Path not found: {path}"})

            matches: list[dict[str, Any]] = []
            total_matches = 0

            for file_path in files_to_search:
                try:
                    lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    continue

                for line_num, line in enumerate(lines, 1):
                    if regex.search(line):
                        total_matches += 1
                        if len(matches) < max_results:
                            rel_path = (
                                file_path.relative_to(base_path)
                                if base_path.is_dir()
                                else file_path
                            )
                            matches.append(
                                {
                                    "file": str(rel_path),
                                    "line": line_num,
                                    "content": line[:200],  # Truncate long lines
                                }
                            )

                if len(matches) >= max_results:
                    break

            return json.dumps(
                {
                    "pattern": pattern,
                    "path": str(base_path.resolve()),
                    "case_sensitive": case_sensitive,
                    "whole_word": whole_word,
                    "total_matches": total_matches,
                    "returned": len(matches),
                    "matches": matches,
                }
            )

        except re.error as e:
            return json.dumps({"error": f"Invalid regex pattern: {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Error searching: {str(e)}"})
