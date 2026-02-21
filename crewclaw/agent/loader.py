"""Agents Loader for dynamically registering CrewAI agents from workspace."""

import os
import glob
import yaml
import logging
from typing import List, Dict, Any
from crewai import Agent
from crewclaw.config import get_config

logger = logging.getLogger(__name__)

class AgentsLoader:
    """Loads and registers agents from a directory."""
    
    def __init__(self, agents_dir: str | None = None):
        config = get_config()
        self.agents_dir = agents_dir or config.get("project.agents_dir", "./workspace/agents")
        self.agents: Dict[str, Agent] = {}

    def load_all(self, tool_registry: list | None = None) -> Dict[str, Agent]:
        """Scan directory and load all agents from .md and .yaml files."""
        if not os.path.exists(self.agents_dir):
            os.makedirs(self.agents_dir, exist_ok=True)
            logger.info(f"Created agents directory: {self.agents_dir}")
            return {}

        # Load YAML definitions
        for yaml_file in glob.glob(os.path.join(self.agents_dir, "*.yaml")):
            self._load_from_yaml(yaml_file, tool_registry)

        # Load Markdown definitions
        for md_file in glob.glob(os.path.join(self.agents_dir, "*.md")):
            self._load_from_markdown(md_file, tool_registry)
            
        return self.agents

    def _load_from_yaml(self, file_path: str, tool_registry: list | None):
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            if not config:
                return
            
            for name, settings in config.items():
                self._create_and_register(name, settings, tool_registry)
        except Exception as e:
            logger.error(f"Error loading agents from {file_path}: {e}")

    def _load_from_markdown(self, file_path: str, tool_registry: list | None):
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Use frontmatter-style parsing
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    if meta and "name" in meta:
                        self._create_and_register(meta["name"], meta, tool_registry)
        except Exception as e:
            logger.error(f"Error loading agent from {file_path}: {e}")

    def _create_and_register(self, name: str, config: Dict[str, Any], tool_registry: list | None):
        try:
            # Map tools from names to actual tool objects if tool_registry provided
            agent_tools = []
            if "tools" in config and tool_registry:
                requested_tools = config["tools"]
                for tool in tool_registry:
                    if hasattr(tool, 'name') and tool.name in requested_tools:
                        agent_tools.append(tool)
            
            agent = Agent(
                role=config.get("role", name),
                goal=config.get("goal", ""),
                backstory=config.get("backstory", ""),
                verbose=config.get("verbose", True),
                allow_delegation=config.get("allow_delegation", False),
                tools=agent_tools,
                max_iter=config.get("max_iter", 15),
                memory=config.get("memory", True)
            )
            self.agents[name] = agent
            logger.info(f"Loaded dynamic agent: {name}")
        except Exception as e:
            logger.error(f"Failed to create agent {name}: {e}")

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)
