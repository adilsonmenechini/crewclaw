"""Tasks Loader for dynamically registering CrewAI tasks from workspace."""

import os
import glob
import yaml
import logging
from pathlib import Path
from typing import Dict, Any
from crewai import Task
from crewclaw.config import get_config

logger = logging.getLogger(__name__)


class TasksLoader:
    """Loads and registers tasks from a directory."""

    def __init__(self, tasks_dir: str | None = None):
        config = get_config()
        self.workspace_dir = tasks_dir or config.get("project.tasks_dir", "./workspace/tasks")
        self.base_dir = str(Path(__file__).parent.parent / "base" / "tasks")
        self.tasks: Dict[str, Task] = {}

    def load_all(self, agent_registry: dict | None = None) -> Dict[str, Task]:
        """Scan both base and workspace directories, base first."""
        # 1. Load from Base (Persistent)
        if os.path.exists(self.base_dir):
            self._load_from_dir(self.base_dir, agent_registry, is_template=True)

        # 2. Load from Workspace (Ephemeral/User)
        if not os.path.exists(self.workspace_dir):
            os.makedirs(self.workspace_dir, exist_ok=True)
        else:
            self._load_from_dir(self.workspace_dir, agent_registry, is_template=False)

        return self.tasks

    def _load_from_dir(self, directory: str, agent_registry: dict | None, is_template: bool):
        pattern = "*.yaml.template" if is_template else "*.yaml"
        for yaml_file in glob.glob(os.path.join(directory, pattern)):
            self._load_from_yaml(yaml_file, agent_registry, is_template)

        for md_file in glob.glob(os.path.join(directory, "*.md")):
            self._load_from_markdown(md_file, agent_registry)

    def _render_template(self, content: str) -> str:
        """Render template with config values."""
        from crewclaw.config import get_config

        config = get_config()
        ai_name = config.get("ai.name", "CrewClaw")
        objective = config.get("ai.objective", "Assist with SRE, automation and task management")

        mapping = {
            "ai_name": ai_name,
            "objective": objective,
        }

        for key, value in mapping.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

    def _load_from_yaml(
        self, file_path: str, agent_registry: dict | None, is_template: bool = False
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
                self._create_and_register(name, settings, agent_registry)
        except Exception as e:
            logger.error(f"Error loading tasks from {file_path}: {e}")

    def _load_from_markdown(self, file_path: str, agent_registry: dict | None):
        try:
            with open(file_path, "r") as f:
                content = f.read()

            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    meta = yaml.safe_load(parts[1])
                    if meta and "name" in meta:
                        self._create_and_register(meta["name"], meta, agent_registry)
        except Exception as e:
            logger.error(f"Error loading task from {file_path}: {e}")

    def _create_and_register(self, name: str, config: Dict[str, Any], agent_registry: dict | None):
        try:
            agent = None
            if "agent" in config and agent_registry:
                agent_name = config["agent"]
                agent = agent_registry.get(agent_name)

            task = Task(
                description=config.get("description", ""),
                expected_output=config.get("expected_output", ""),
                agent=agent,
                async_execution=config.get("async_execution", False),
                context=config.get("context", []),
            )
            self.tasks[name] = task
            logger.info(f"Loaded dynamic task: {name}")
        except Exception as e:
            logger.error(f"Failed to create task {name}: {e}")

    def get_task(self, name: str) -> Task | None:
        return self.tasks.get(name)
