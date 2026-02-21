"""Soul and Personality management for CrewClaw."""

import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SoulManager:
    """Manages the agent's identity and evolution via soul.md."""
    
    def __init__(self, soul_path: str | None = None):
        from crewclaw.config import get_config
        config = get_config()
        self.soul_path = soul_path or config.get("project.soul_path", "./workspace/memory/soul.md")
        self.identity: Dict[str, Any] = {}
        self.evolution_log: list = []

    def load_soul(self):
        """Read soul.md and parse personality traits."""
        if not os.path.exists(self.soul_path):
            logger.info("No soul.md found. Creating a default soul.")
            self._create_default_soul()
            return

        with open(self.soul_path, 'r') as f:
            content = f.read()
            # Simple parsing for identity sections
            # In a real implementation, this would use a more robust Markdown parser
            self.identity["content"] = content

    def _create_default_soul(self):
        default_content = """# Soul of CrewClaw Agent

## Identity
- **Name**: CrewClaw
- **Voice**: Professional and helpful.

## Values
- Prioritize local privacy and system security.
"""
        with open(self.soul_path, 'w') as f:
            f.write(default_content)
        self.identity["content"] = default_content

    def evolve(self, new_insight: str):
        """Add a new insight to the soul file."""
        with open(self.soul_path, 'a') as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d")
            f.write(f"\n- [{timestamp}]: {new_insight}")
        logger.info(f"Soul evolved with new insight: {new_insight}")

    def get_system_prompt_addition(self) -> str:
        """Return the soul content to be injected into the system prompt."""
        return f"\n\nCORE IDENTITY & PERSONALITY:\n{self.identity.get('content', '')}"
