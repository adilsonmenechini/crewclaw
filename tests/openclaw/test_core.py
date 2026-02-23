import pytest
import os
import asyncio
from unittest.mock import MagicMock, patch
from crewclaw.agent.memory.soul import SoulManager
from crewclaw.agent.tools.loader import SkillsLoader
from crewclaw.agent.tools.dynamic import DynamicSkill, parse_skill_markdown
from crewclaw.agent.scheduler import HookManager, HeartbeatManager
from crewclaw.agent.bridge import ChannelBridge, BaseChannel
from crewclaw.agent.self_improvement import SelfImprovementLoop
from crewclaw.agent.loader import AgentsLoader
from crewclaw.agent.task_loader import TasksLoader
from crewclaw.agent.tools.mcp_loader import MCPLoader


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


# SoulManager Tests
def test_soul_manager_creation(temp_dir):
    soul_path = temp_dir / "soul.md"
    manager = SoulManager(str(soul_path))
    manager.load_soul()
    assert os.path.exists(soul_path)
    assert "CrewClaw" in manager.get_system_prompt_addition()


def test_soul_manager_evolution(temp_dir):
    soul_path = temp_dir / "soul.md"
    manager = SoulManager(str(soul_path))
    manager.load_soul()
    manager.evolve("Test insight")
    with open(soul_path, "r") as f:
        content = f.read()
    assert "Test insight" in content


# Dynamic Skill & Loader Tests
def test_parse_skill_markdown():
    content = """---
name: "test_tool"
description: "A test tool"
---
```python
def execute(n=1):
    return n * 2
```"""
    parsed = parse_skill_markdown(content)
    assert parsed["metadata"]["name"] == "test_tool"
    assert "def execute" in parsed["code"]


def test_skills_loader(temp_dir):
    skills_dir = temp_dir / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "hello.md"
    skill_file.write_text("""---
name: "hello"
---
```python
def execute(name='World'):
    return f'Hello {name}'
```""")

    loader = SkillsLoader(str(skills_dir))
    loader.load_all()
    tools = loader.get_tools()
    assert len(tools) == 1
    assert tools[0].name == "hello"


@pytest.mark.asyncio
async def test_dynamic_skill_execution():
    async def mock_exec(val):
        return f"Result: {val}"

    skill = DynamicSkill("test", "desc", {}, mock_exec)
    result = await skill.execute(val="OK")
    assert result == "Result: OK"


# Scheduler Tests
def test_hook_manager_add():
    mgr = HookManager()
    mgr.add_hook("test", "1 minute", "shell", "echo 1")
    # Verify schedule has 1 job
    import schedule

    assert len(schedule.get_jobs()) >= 1
    schedule.clear()


@pytest.mark.asyncio
async def test_heartbeat_loop():
    # We use a short sleep and then stop the manager
    # mocking asyncio.sleep to not actually wait
    with patch("asyncio.sleep", side_effect=[None, asyncio.CancelledError()]):
        mgr = HeartbeatManager(MagicMock())
        try:
            await mgr.start(1)
        except asyncio.CancelledError:
            pass


# Bridge Tests
@pytest.mark.asyncio
async def test_channel_bridge():
    mock_agent = MagicMock()
    bridge = ChannelBridge(mock_agent)
    mock_channel = MagicMock(spec=BaseChannel)
    bridge.add_channel("test", mock_channel)
    assert "test" in bridge.channels

    await bridge.handle_incoming("test", "hello", "user1")
    # Verify logging or interaction (currently logic is placeholder)


# Self-Improvement Tests
@pytest.mark.asyncio
async def test_self_improvement_scan(temp_dir):
    logs_dir = temp_dir / "logs"
    logs_dir.mkdir()
    log_file = logs_dir / "error.log"
    log_file.write_text("2026-02-21 ERROR: Sample error\n")

    si = SelfImprovementLoop(str(logs_dir), str(temp_dir))
    analysis = await si.run_analysis()
    assert "Reflection triggered" in analysis
    assert len(si._scan_logs_for_errors()) == 1


# AgentsLoader Tests
def test_agents_loader_yaml(temp_dir):
    with patch("crewclaw.agent.loader.Agent") as MockAgent:
        agents_dir = temp_dir / "agents"
        agents_dir.mkdir()
        agent_yaml = agents_dir / "test_agent.yaml"
        agent_yaml.write_text("""
test_bot:
  role: "Tester"
  goal: "Verify loading"
  backstory: "A simple bot for testing"
""")

        loader = AgentsLoader(str(agents_dir))
        agents = loader.load_all()
        assert "test_bot" in agents
        MockAgent.assert_called()


def test_agents_loader_markdown(temp_dir):
    with patch("crewclaw.agent.loader.Agent") as MockAgent:
        agents_dir = temp_dir / "agents"
        if not agents_dir.exists():
            agents_dir.mkdir()
        agent_md = agents_dir / "bot.md"
        agent_md.write_text("""---
name: "md_bot"
role: "Markdown Bot"
goal: "Test MD loading"
---
# Bot Info
Description here...
""")

        loader = AgentsLoader(str(agents_dir))
        agents = loader.load_all()
        assert "md_bot" in agents
        MockAgent.assert_called()


# TasksLoader Tests
def test_tasks_loader_yaml(temp_dir):
    tasks_dir = temp_dir / "tasks"
    tasks_dir.mkdir()
    task_yaml = tasks_dir / "test_task.yaml"
    task_yaml.write_text("""
analyze_logs:
  description: "Check errors"
  expected_output: "Report"
""")

    loader = TasksLoader(str(tasks_dir))
    tasks = loader.load_all()
    assert "analyze_logs" in tasks
    assert tasks["analyze_logs"].description == "Check errors"


def test_tasks_loader_markdown(temp_dir):
    tasks_dir = temp_dir / "tasks"
    if not tasks_dir.exists():
        tasks_dir.mkdir()
    task_md = tasks_dir / "mission.md"
    task_md.write_text("""---
name: "mission_a"
description: "Secret mission"
expected_output: "Success"
---
# Mission A
More details...
""")

    loader = TasksLoader(str(tasks_dir))
    tasks = loader.load_all()
    assert "mission_a" in tasks
    assert tasks["mission_a"].description == "Secret mission"


# MCPLoader Tests
def test_mcp_loader_json(temp_dir):
    mcp_dir = temp_dir / "mcp"
    mcp_dir.mkdir()
    mcp_json = mcp_dir / "test_server.json"
    mcp_json.write_text('{"command": "npx", "args": ["@modelcontextprotocol/server-everything"]}')

    loader = MCPLoader(str(mcp_dir))
    servers = loader.load_all()
    assert "test_server" in servers
    assert servers["test_server"]["command"] == "npx"


# Custom Tools Loader Tests
def test_custom_python_tools_loader(temp_dir):
    tools_dir = temp_dir / "custom_tools"
    tools_dir.mkdir()
    tool_py = tools_dir / "my_tool.py"
    tool_py.write_text("""
from crewclaw.agent.tools.base import Tool
from typing import Any

class MyCustomTool(Tool):
    @property
    def name(self) -> str: return "custom_python_tool"
    @property
    def description(self) -> str: return "A tool written in pure Python"
    @property
    def parameters(self) -> dict[str, Any]: return {"type": "object", "properties": {}}
    
    async def execute(self, **kwargs: Any) -> str:
        return "Python Power!"
""")

    loader = SkillsLoader(custom_tools_dir=str(tools_dir))
    loader.load_all()
    tools = {t.name: t for t in loader.get_tools()}
    assert "custom_python_tool" in tools
    assert tools["custom_python_tool"].description == "A tool written in pure Python"
