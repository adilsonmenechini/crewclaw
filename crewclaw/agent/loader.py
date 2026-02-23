"""Agents Loader for dynamically registering CrewAI agents from workspace."""

import os
import glob
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from crewai import Agent
from crewclaw.config import get_config
from crewclaw.providers.crewai import LiteLLMForCrewAI

logger = logging.getLogger(__name__)


class AgentsLoader:
    """Loads and registers agents from a directory."""

    def __init__(self, agents_dir: str | None = None):
        config = get_config()
        self.workspace_dir = agents_dir or config.get("project.agents_dir", "./workspace/agents")
        self.base_dir = str(Path(__file__).parent.parent / "base" / "agents")
        self.skills_dir = config.get("project.skills_dir", "./workspace/skills")
        self.base_skills_dir = str(Path(__file__).parent.parent / "base" / "skills")
        self.agents: Dict[str, Agent] = {}

    def load_all(self, tool_registry: list | None = None) -> Dict[str, Agent]:
        """Scan both base and workspace directories, base first."""
        # 1. Load from Base (Persistent)
        if os.path.exists(self.base_dir):
            self._load_from_dir(self.base_dir, tool_registry, is_template=True)

        # 2. Load from Workspace (Ephemeral/User)
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir, exist_ok=True)
        else:
            self._load_from_dir(self.workspace_dir, tool_registry, is_template=False)

        return self.agents

    def _load_from_dir(self, directory: str, tool_registry: list | None, is_template: bool):
        pattern = "*.yaml.template" if is_template else "*.yaml"
        for yaml_file in glob.glob(os.path.join(directory, pattern)):
            self._load_from_yaml(yaml_file, tool_registry, is_template)

        for md_file in glob.glob(os.path.join(directory, "*.md")):
            self._load_from_markdown(md_file, tool_registry)

    def _render_template(self, content: str) -> str:
        """Render template with config values."""
        import re
        from crewclaw.config import get_config

        config = get_config()
        ai_name = config.get("ai.name", "CrewClaw")
        objective = config.get("ai.objective", "Assist with SRE, automation and task management")

        # Simple rendering logic matching cli/templates
        mapping = {
            "ai_name": ai_name,
            "objective": objective,
            "role": "Specialist",
            "backstory": "Expert AI",
            "tools": "[]",
        }

        for key, value in mapping.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

        # Remove any leftover Jinja2-style tags (% ... %)
        content = re.sub(r"{%.*?%}", "", content, flags=re.DOTALL)

        return content

    def _load_from_yaml(
        self, file_path: str, tool_registry: list | None, is_template: bool = False
    ):
        try:
            with open(file_path, "r") as f:
                content = f.read()

            if is_template:
                content = self._render_template(content)

            config = yaml.safe_load(content)
            if not config:
                return

            for name, settings in config.items():
                self._create_and_register(name, settings, tool_registry)
        except Exception as e:
            logger.error(f"Error loading agents from {file_path}: {e}")

    def _load_from_markdown(self, file_path: str, tool_registry: list | None):
        try:
            with open(file_path, "r") as f:
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

    def _load_skill_content(self, skill_name: str) -> str:
        """Load skill content from workspace or base directory."""
        # Try workspace first
        workspace_skill = Path(self.skills_dir) / f"{skill_name}.md"
        if workspace_skill.exists():
            return workspace_skill.read_text()

        # Try base
        base_skill = Path(self.base_skills_dir) / f"{skill_name}.md.template"
        if base_skill.exists():
            return base_skill.read_text()

        # Try .md in base just in case
        base_skill_md = Path(self.base_skills_dir) / f"{skill_name}.md"
        if base_skill_md.exists():
            return base_skill_md.read_text()

        return ""

    def _create_and_register(self, name: str, config: Dict[str, Any], tool_registry: list | None):
        try:
            # Map tools from names to actual tool objects if tool_registry provided
            agent_tools = []
            if "tools" in config and tool_registry:
                requested_tools = config["tools"]
                for tool in tool_registry:
                    if hasattr(tool, "name") and tool.name in requested_tools:
                        agent_tools.append(tool)

            # Handle skills injection
            backstory = config.get("backstory", "")
            if "skills" in config:
                for skill_name in config["skills"]:
                    skill_content = self._load_skill_content(skill_name)
                    if skill_content:
                        backstory += (
                            f"\n\nADDITIONAL KNOWLEDGE (Skill: {skill_name}):\n{skill_content}"
                        )

            agent = Agent(
                role=config.get("role", name),
                goal=config.get("goal", ""),
                backstory=backstory,
                verbose=config.get("verbose", True),
                allow_delegation=config.get("allow_delegation", False),
                tools=agent_tools,
                llm=LiteLLMForCrewAI(),
                max_iter=config.get("max_iter", 15),
                memory=config.get("memory", True),
            )
            self.agents[name] = agent
            logger.info(f"Loaded dynamic agent: {name}")
        except Exception as e:
            logger.error(f"Failed to create agent {name}: {e}")

    def get_agent(self, name: str) -> Agent | None:
        return self.agents.get(name)
