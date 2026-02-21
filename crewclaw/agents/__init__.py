"""Agents module for CrewClaw."""

from .factory import AgentFactory
from .crew import create_crew, create_task
from .samples import (
    create_researcher_agent,
    create_writer_agent,
    create_analyzer_agent,
    get_sample_agent,
    SAMPLE_AGENTS,
)

__all__ = [
    "AgentFactory",
    "create_crew",
    "create_task",
    "create_researcher_agent",
    "create_writer_agent",
    "create_analyzer_agent",
    "get_sample_agent",
    "SAMPLE_AGENTS",
]
