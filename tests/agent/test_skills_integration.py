import os
import pytest
from unittest.mock import patch
from crewclaw.agent.tools.loader import SkillsLoader
from crewclaw.agent.loader import AgentsLoader


@pytest.fixture
def temp_skills_dir(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    return str(skills_dir)


def test_skills_loader_markdown_parsing(temp_skills_dir):
    skill_file = os.path.join(temp_skills_dir, "test_skill.md")
    with open(skill_file, "w") as f:
        f.write("""---
name: "math_add"
description: "Adds two numbers"
parameters:
  type: object
  properties:
    a: {type: number}
    b: {type: number}
---
```python
def execute(a, b):
    return a + b
```""")

    loader = SkillsLoader(skills_dir=temp_skills_dir)
    loader.load_all()

    assert "math_add" in loader.tools
    skill = loader.tools["math_add"]
    assert skill.description == "Adds two numbers"

    # Test execution
    import asyncio

    result = asyncio.run(skill.execute(a=10, b=5))
    assert result == 15


def test_agents_loader_skills_injection(tmp_path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    skill_file = skills_dir / "useful_info.md"
    skill_file.write_text("# Knowledge\nThis is a secret.")

    agent_yaml = agents_dir / "assistant.yaml"
    agent_yaml.write_text("""
assistant:
  role: "Helper"
  goal: "Help user"
  backstory: "Default backstory"
  skills: ["useful_info"]
""")

    # Mocking config to point to these dirs
    with patch("crewclaw.config.get_config") as mock_config:
        mock_config.return_value.get.side_effect = lambda k, default=None: {
            "project.agents_dir": str(agents_dir),
            "project.skills_dir": str(skills_dir),
        }.get(k, default)

        loader = AgentsLoader(agents_dir=str(agents_dir))
        # Pointing to the right skills dir for the loader instance too
        loader.skills_dir = str(skills_dir)

        agents = loader.load_all()
        assert "assistant" in agents
        assistant = agents["assistant"]

        assert "This is a secret" in assistant.backstory
        assert "Default backstory" in assistant.backstory
