"""Core agent logic for CrewClaw."""

from .factory import AgentFactory
from .loader import AgentsLoader
from .task_loader import TasksLoader
from .crew import create_crew, create_task
from .loop import ReActRuntime
from .samples import (
    create_researcher_agent,
    create_writer_agent,
    get_sample_agent,
    SAMPLE_AGENTS,
)

__all__ = [
    "AgentFactory",
    "AgentsLoader",
    "TasksLoader",
    "create_crew",
    "create_task",
    "ReActRuntime",
    "create_researcher_agent",
    "create_writer_agent",
    "get_sample_agent",
    "SAMPLE_AGENTS",
]
