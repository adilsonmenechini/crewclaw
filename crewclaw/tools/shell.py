"""Shell execution tool with security hardening."""

import asyncio
import os
import re
import shlex
from pathlib import Path
from typing import Any

from crewclaw.tools.base import Tool

# Allowlist of safe commands for subprocess execution
SAFE_COMMANDS = {
    # Version control
    "git",
    "gh",
    "hg",
    # File operations
    "ls",
    "cat",
    "head",
    "tail",
    "wc",
    "sort",
    "uniq",
    "cut",
    "tr",
    "paste",
    "find",
    "locate",
    "xargs",
    "cp",
    "mv",
    "rm",
    "mkdir",
    "touch",
    "chmod",
    "chown",
    # Text processing
    "grep",
    "egrep",
    "fgrep",
    "sed",
    "awk",
    "jq",
    "yq",
    # System info
    "pwd",
    "whoami",
    "hostname",
    "uname",
    "date",
    "which",
    "file",
    "stat",
    # Process management
    "ps",
    "kill",
    "killall",
    "pkill",
    # Compression
    "tar",
    "gzip",
    "gunzip",
    "bz2",
    "bunzip2",
    "zip",
    "unzip",
    "xz",
    "unxz",
    # Networking (read-only)
    "curl",
    "wget",
    "ping",
    "traceroute",
    "dig",
    "nslookup",
    "netstat",
    "ss",
    # Docker/Containers
    "docker",
    "docker-compose",
    "podman",
    "kubectl",
    "helm",
    # Dev tools
    "python",
    "python3",
    "pip",
    "pip3",
    "uv",
    "npm",
    "yarn",
    "node",
    # Cloud CLI (read-only or limited)
    "aws",
    "gcloud",
    "az",
    # Terraform/IaC (read-only operations)
    "terraform",
    "terragrunt",
    # Utilities
    "echo",
    "printf",
    "yes",
    "sleep",
    "true",
    "false",
    "test",
    # Directory change
    "cd",
    "env",
    "export",
    "unset",
    "source",
}

# Regex para detectar metacaracteres perigosos de shell
SHELL_METACHARACTERS = re.compile(r"[;&|$`<>(){}[\]\\*?\n\r]")

# Padrões de comando perigosos para bloquear
DANGEROUS_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",  # rm -r, rm -rf
    r"\bdel\s+/[fq]\b",  # Windows del
    r"\bformat\b",  # format disk
    r"\bmkfs\b",  # make filesystem
    r">\s*/dev/[sv]d",  # write to disk device
    r"\bdd\s+if=",  # dd if= (pode ler device)
    r"\b(shutdown|reboot|poweroff|halt)\b",  # system power
    r":\(\)\s*\{.*\};\s*:",  # fork bomb
    r"\|\s*\|\|",  # command chaining after pipe
    r"&&\s*\w+\s*;",  # command chaining
    r"\$\([^)]+\)",  # command substitution $(...)
    r"`[^`]+`",  # backtick substitution
]


class ExecTool(Tool):
    """Tool to execute shell commands with security hardening."""

    def __init__(
        self,
        timeout: int = 60,
        working_dir: str | None = None,
        deny_patterns: list[str] | None = None,
        allow_patterns: list[str] | None = None,
        restrict_to_workspace: bool = False,
        workspace: Path | None = None,
    ):
        self.timeout = timeout
        self.working_dir = working_dir
        self.workspace = workspace
        self.restrict_to_workspace = restrict_to_workspace
        self.deny_patterns = deny_patterns or DANGEROUS_PATTERNS
        self.allow_patterns = allow_patterns or list(SAFE_COMMANDS)

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return "Execute a shell command and return its output. Commands are restricted to a safe allowlist."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute"},
                "working_dir": {
                    "type": "string",
                    "description": "Optional working directory for the command",
                },
            },
            "required": ["command"],
        }

    def _validate_command(self, command: str) -> tuple[bool, str]:
        """
        Validate command for security issues.

        Returns:
            tuple: (is_valid, error_message)
        """
        cmd = command.strip()
        lower = cmd.lower()

        # 1. Check for shell metacharacters (indicates injection attempt)
        if SHELL_METACHARACTERS.search(command):
            return (
                False,
                "Error: Command blocked - shell metacharacters detected (;|&$`<>(){}[]\\*?\\n\\r)",
            )

        # 2. Check for dangerous patterns
        for pattern in self.deny_patterns:
            if re.search(pattern, lower):
                return (
                    False,
                    f"Error: Command blocked by safety guard (dangerous pattern matched: {pattern})",
                )

        # 3. Check if first command is in allowlist
        first_cmd = cmd.split()[0] if cmd else ""
        # Handle quoted commands
        if first_cmd.startswith('"') or first_cmd.startswith("'"):
            first_cmd = shlex.split(cmd)[0] if shlex.split(cmd) else first_cmd

        if first_cmd and first_cmd not in SAFE_COMMANDS:
            return False, f"Error: Command '{first_cmd}' is not in the allowed commands list"

        # 4. Workspace restriction
        if self.restrict_to_workspace and self.workspace:
            cwd_path = Path(self.working_dir or os.getcwd()).resolve()
            workspace_resolved = self.workspace.resolve()

            # Check for path traversal attempts
            if ".." in cmd.replace("\\", "/").split("/"):
                return False, "Error: Command blocked - path traversal detected"

            # Extract and validate paths in command
            posix_paths = re.findall(r"/[^\s\"']+", cmd)
            for raw in posix_paths:
                try:
                    p = Path(raw).resolve()
                    # Check if path is outside workspace
                    try:
                        p.relative_to(workspace_resolved)
                    except ValueError:
                        # Check if it's at least under cwd
                        if cwd_path not in p.parents and p != cwd_path:
                            return (
                                False,
                                f"Error: Command blocked - path '{raw}' is outside allowed directories",
                            )
                except (OSError, ValueError):
                    continue

        return True, ""

    async def execute(self, **kwargs: Any) -> str:
        command = kwargs.get("command", "")
        working_dir = kwargs.get("working_dir")

        is_valid, error_msg = self._validate_command(command)
        if not is_valid:
            return error_msg

        cwd = working_dir or self.working_dir or os.getcwd()

        try:
            args = shlex.split(command)
            if not args:
                return "Error: Empty command"

            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=self.timeout)
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: Command timed out after {self.timeout} seconds"

            output_parts = []

            if stdout:
                output_parts.append(stdout.decode("utf-8", errors="replace"))

            if stderr:
                stderr_text = stderr.decode("utf-8", errors="replace")
                if stderr_text.strip():
                    output_parts.append(f"STDERR:\n{stderr_text}")

            if process.returncode != 0:
                output_parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(output_parts) if output_parts else "(no output)"

            max_len = 10000
            if len(result) > max_len:
                result = result[:max_len] + f"\n... (truncated, {len(result) - max_len} more chars)"

            return result

        except Exception as e:
            return f"Error executing command: {str(e)}"
