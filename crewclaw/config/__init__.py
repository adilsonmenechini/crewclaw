"""Configuration module for CrewClaw."""

import json
import os
from pathlib import Path
from typing import Any


class Config:
    """Configuration manager for CrewClaw."""

    _instance = None
    _config: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._config:
            self.load()

    def load(self, config_path: str | None = None) -> None:
        """Load configuration from file."""
        # Load environment variables from .env if it exists
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        if config_path is None:
            config_path = os.environ.get("CREWCLAW_CONFIG", "crewclaw.json")

        path = Path(config_path)
        if path.exists():
            with open(path) as f:
                self._config = json.load(f)
        else:
            self._config = self._get_defaults()

    def _get_defaults(self) -> dict:
        """Return default configuration."""
        return {
            "version": "1.0.0",
            "project": {
                "name": "crewclaw",
                "memory_dir": "./workspace/memory",
                "database_path": "./workspace/memory/crewclaw.db",
                "soul_path": "./workspace/memory/soul.md",
                "skills_dir": "./workspace/skills",
                "agents_dir": "./workspace/agents",
                "tasks_dir": "./workspace/tasks",
                "mcp_dir": "./workspace/mcp",
                "custom_tools_dir": "./workspace/custom_tools",
            },
            "llm": {
                "provider": "openrouter",
                "model": "openrouter/google/gemini-2.0-flash-lite",
                "fallback": {
                    "provider": "google",
                    "model": "gemini-2.0-flash",
                },
                "api_key_env": "OPENROUTER_API_KEY",
            },
            "user": {
                "name": "User",
            },
            "ai": {
                "name": "CrewClaw",
                "objective": "Assist with SRE, automation and task management",
            },
            "telegram": {
                "enabled": False,
                "token_env": "TELEGRAM_BOT_TOKEN",
            },
            "embedding": {
                "provider": "sentence-transformers",
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "dimension": 384,
            },
            "chunking": {
                "chunk_size": 500,
                "chunk_overlap": 50,
                "syntax_aware": True,
            },
            "search": {
                "fts5_enabled": True,
                "vector_enabled": True,
                "default_limit": 5,
            },
            "runtime": {
                "max_iterations": 20,
                "max_execution_time": 300,
                "max_retry_limit": 2,
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation key."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-notation key."""
        keys = key.split(".")
        config = self._config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value

    @property
    def config(self) -> dict:
        """Return full configuration."""
        return self._config


def get_config() -> Config:
    """Get singleton config instance."""
    return Config()
