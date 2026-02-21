"""Dynamic Skill implementation for CrewClaw."""

import yaml
import re
from typing import Any, Callable
from crewclaw.agent.tools.base import Tool

class DynamicSkill(Tool):
    """
    A Tool that can be dynamically defined from a configuration/markdown.
    """

    def __init__(self, name: str, description: str, parameters: dict[str, Any], execute_fn: Callable):
        self._name = name
        self._description = description
        self._parameters = parameters
        self._execute_fn = execute_fn

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> str:
        if self._execute_fn:
            import inspect
            if inspect.iscoroutinefunction(self._execute_fn):
                return await self._execute_fn(**kwargs)
            else:
                return self._execute_fn(**kwargs)
        return "Error: No execution function defined for this dynamic skill."

def parse_skill_markdown(content: str) -> dict[str, Any]:
    """Parse skill metadata and code from markdown."""
    frontmatter_match = re.search(r'^---(.*?)---', content, re.DOTALL | re.MULTILINE)
    code_match = re.search(r'```python(.*?)```', content, re.DOTALL)
    
    metadata = {}
    if frontmatter_match:
        try:
            metadata = yaml.safe_load(frontmatter_match.group(1))
        except yaml.YAMLError:
            pass
            
    code = ""
    if code_match:
        code = code_match.group(1).strip()
        
    return {
        "metadata": metadata,
        "code": code
    }
