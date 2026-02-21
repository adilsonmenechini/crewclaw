"""Agent factory for creating CrewAI agents from configuration."""

import os
from pathlib import Path
from typing import Any

import yaml

from crewai import Agent
from crewai.memory import memory as crewai_memory

# Type alias for CrewAI Memory - must be after crewai_memory import
Memory = crewai_memory.Memory

from ..config import get_config  # noqa: E402
from ..config.logging import get_logger  # noqa: E402

logger = get_logger(__name__)


class AgentFactory:
    """Factory for creating CrewAI agents from YAML configuration."""

    def __init__(self, config_path: str | None = None):
        """Initialize factory.

        Args:
            config_path: Path to agents.yaml file.
        """
        # Default to config/agents.yaml in project root
        if config_path is None:
            config_path = os.environ.get("CREWCLAW_AGENTS_CONFIG", "config/agents.yaml")

        self.config_path = Path(config_path)
        self._agents_config: dict | None = None

    @property
    def agents_config(self) -> dict:
        """Load and cache agents configuration."""
        if self._agents_config is None:
            self._agents_config = self._load_config()
        return self._agents_config

    def _load_config(self) -> dict:
        """Load agents configuration from YAML."""
        if not self.config_path.exists():
            logger.warning(f"Agents config not found: {self.config_path}")
            return {}

        with open(self.config_path) as f:
            return yaml.safe_load(f) or {}

    def create_agent(
        self,
        name: str,
        tools: list[Any] | None = None,
        memory: Memory | None = None,
        **override_kwargs,
    ) -> Agent:
        """Create agent from configuration.

        Args:
            name: Agent name (key in agents.yaml).
            tools: Additional tools to add.
            memory: Memory instance.
            **override_kwargs: Override config values.

        Returns:
            CrewAI Agent instance.
        """
        config = self.agents_config.get(name, {})

        if not config:
            raise ValueError(f"Agent '{name}' not found in config")

        # Apply variable substitution
        inputs = get_config().config
        for key in ["role", "goal", "backstory"]:
            if key in config:
                config[key] = self._substitute_variables(config[key], inputs)

        # Build agent kwargs
        kwargs = {
            "role": config.get("role", name),
            "goal": config.get("goal", ""),
            "backstory": config.get("backstory", ""),
            "verbose": config.get("verbose", False),
            "allow_delegation": config.get("allow_delegation", False),
            "max_iter": config.get("max_iter", 20),
            "max_retry_limit": config.get("max_retry_limit", 2),
        }

        # Add tools
        agent_tools = list(tools) if tools else []
        if config.get("tools"):
            # Import tools dynamically
            for tool_name in config["tools"]:
                try:
                    from crewai_tools import import_tool

                    tool = import_tool(tool_name)
                    agent_tools.append(tool)
                except Exception as e:
                    logger.warning(f"Failed to load tool {tool_name}: {e}")

        if agent_tools:
            kwargs["tools"] = agent_tools

        # Add memory
        if memory:
            kwargs["memory"] = memory

        # Apply overrides
        kwargs.update(override_kwargs)

        logger.info(f"Created agent: {name}")
        return Agent(**kwargs)

    def _substitute_variables(self, text: str, context: dict) -> str:
        """Substitute {variable} placeholders in text.

        Args:
            text: Text with placeholders.
            context: Context for substitution.

        Returns:
            Text with variables substituted.
        """
        import re

        def replace(match):
            key = match.group(1)
            # Look up in context (supports nested keys)
            keys = key.split(".")
            value = context
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    return match.group(0)
            return str(value) if value is not None else match.group(0)

        return re.sub(r"\{(\w+(?:\.\w+)*)\}", replace, text)

    def list_agents(self) -> list[str]:
        """List available agent names.

        Returns:
            List of agent names.
        """
        return list(self.agents_config.keys())
