"""Tasks Loader for dynamically registering CrewAI tasks from workspace."""

import os
import glob
import yaml
import logging
from typing import List, Dict, Any
from crewai import Task
from crewclaw.config import get_config

logger = logging.getLogger(__name__)

class TasksLoader:
    """Loads and registers tasks from a directory."""
    
    def __init__(self, tasks_dir: str | None = None):
        config = get_config()
        self.tasks_dir = tasks_dir or config.get("project.tasks_dir", "./workspace/tasks")
        self.tasks: Dict[str, Task] = {}

    def load_all(self, agent_registry: dict | None = None) -> Dict[str, Task]:
        """Scan directory and load all tasks from .md and .yaml files."""
        if not os.path.exists(self.tasks_dir):
            os.makedirs(self.tasks_dir, exist_ok=True)
            logger.info(f"Created tasks directory: {self.tasks_dir}")
            return {}

        # Load YAML definitions
        for yaml_file in glob.glob(os.path.join(self.tasks_dir, "*.yaml")):
            self._load_from_yaml(yaml_file, agent_registry)

        # Load Markdown definitions
        for md_file in glob.glob(os.path.join(self.tasks_dir, "*.md")):
            self._load_from_markdown(md_file, agent_registry)
            
        return self.tasks

    def _load_from_yaml(self, file_path: str, agent_registry: dict | None):
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            if not config:
                return
            
            for name, settings in config.items():
                self._create_and_register(name, settings, agent_registry)
        except Exception as e:
            logger.error(f"Error loading tasks from {file_path}: {e}")

    def _load_from_markdown(self, file_path: str, agent_registry: dict | None):
        try:
            with open(file_path, 'r') as f:
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
                context=config.get("context", [])
            )
            self.tasks[name] = task
            logger.info(f"Loaded dynamic task: {name}")
        except Exception as e:
            logger.error(f"Failed to create task {name}: {e}")

    def get_task(self, name: str) -> Task | None:
        return self.tasks.get(name)
