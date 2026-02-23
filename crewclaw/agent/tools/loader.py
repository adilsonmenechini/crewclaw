"""Skills Loader for dynamically registering tools."""

import os
import glob
import logging
from typing import List, Dict
from crewclaw.agent.tools.base import Tool
from crewclaw.agent.tools.dynamic import DynamicSkill, parse_skill_markdown

logger = logging.getLogger(__name__)


class SkillsLoader:
    """Loads and registers tools (Skills and Custom Tools) from directories."""

    def __init__(self, skills_dir: str | None = None, custom_tools_dir: str | None = None):
        from crewclaw.config import get_config

        config = get_config()
        self.skills_dir = skills_dir or config.get("project.skills_dir", "./workspace/skills")
        self.custom_tools_dir = custom_tools_dir or config.get(
            "project.custom_tools_dir", "./workspace/custom_tools"
        )
        self.tools: Dict[str, Tool] = {}

    def load_all(self):
        """Scan directories and load all tools."""
        self._load_markdown_skills()
        self._load_custom_python_tools()

    def _load_markdown_skills(self):
        if not os.path.exists(self.skills_dir):
            return
        for md_file in glob.glob(os.path.join(self.skills_dir, "*.md")):
            try:
                with open(md_file, "r") as f:
                    content = f.read()

                parsed = parse_skill_markdown(content)
                meta = parsed["metadata"]
                code = parsed["code"]

                if not meta or "name" not in meta:
                    continue

                # Prepare execution function from code
                # WARNING: executing dynamic code has security implications.
                # In a real system, this should be sandboxed.
                exec_globals = {}
                try:
                    exec(code, exec_globals)
                    execute_fn = exec_globals.get("execute")

                    if execute_fn:
                        skill = DynamicSkill(
                            name=meta["name"],
                            description=meta.get("description", "Dynamic Skill"),
                            parameters=meta.get("parameters", {}),
                            execute_fn=execute_fn,
                        )
                        self.tools[meta["name"]] = skill
                        logger.info(f"Loaded dynamic skill: {meta['name']}")
                except Exception as e:
                    logger.error(f"Error executing code for skill {meta['name']}: {e}")

            except Exception as e:
                logger.error(f"Error loading skill from {md_file}: {e}")

    def _load_custom_python_tools(self):
        """Load pure Python tools from custom_tools_dir."""
        if not self.custom_tools_dir or not os.path.exists(self.custom_tools_dir):
            return

        for py_file in glob.glob(os.path.join(self.custom_tools_dir, "*.py")):
            if py_file.endswith("__init__.py"):
                continue
            try:
                # Dynamic import implementation
                import importlib.util

                module_name = os.path.splitext(os.path.basename(py_file))[0]
                spec = importlib.util.spec_from_file_location(module_name, py_file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Look for classes that inherit from Tool/BaseTool
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if isinstance(attr, type) and issubclass(attr, Tool) and attr is not Tool:
                            tool_instance = attr()
                            self.tools[tool_instance.name] = tool_instance
                            logger.info(f"Loaded custom tool class: {tool_instance.name}")
            except Exception as e:
                logger.error(f"Error loading custom tool from {py_file}: {e}")

    def get_tools(self) -> List[Tool]:
        return list(self.tools.values())
