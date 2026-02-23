"""Agent templates and shared utilities."""

from typing import Any

from crewai import Agent
from crewclaw.providers.crewai import LiteLLMForCrewAI
from crewclaw.agent.tools.crewai_tools import (
    WebSearchTool,
    WebFetchTool,
    FileReadToolCrewAI,
    FileWriteToolCrewAI,
    GrepToolCrewAI,
    DirectoryListToolCrewAI,
    MemorySearchToolCrewAI,
    ExecToolCrewAI,
)


def get_llm() -> Any:
    """Get shared LLM instance."""
    return LiteLLMForCrewAI()


# All available tools for template definitions
ALL_TOOLS_LIST = [
    "web_search",
    "web_fetch",
    "file_read",
    "file_write",
    "grep",
    "ls",
    "memory_search",
    "shell",
]


# Actual tool objects for runtime (minimal set kept for backward compatibility)
def get_all_tools():
    return [
        WebSearchTool(),
        WebFetchTool(),
        FileReadToolCrewAI(),
        FileWriteToolCrewAI(),
        GrepToolCrewAI(),
        DirectoryListToolCrewAI(),
        MemorySearchToolCrewAI(),
        ExecToolCrewAI(),
    ]


# Registry for dynamic loading
def get_sample_agent(name: str) -> Agent:
    """Helper to get an agent from base or workspace templates."""
    from crewclaw.agent.loader import AgentsLoader

    loader = AgentsLoader()
    # Load with all available tools to allow mapping
    agents = loader.load_all(tool_registry=get_all_tools())

    agent = agents.get(name)
    if not agent:
        # Fallback to assistant if not found
        agent = agents.get("assistant")

    if not agent:
        raise ValueError(f"Agent '{name}' not found and no default assistant available.")

    return agent


# Backward compatibility layer
def create_researcher_agent() -> Agent:
    return get_sample_agent("researcher")


def create_writer_agent() -> Agent:
    return get_sample_agent("writer")


def create_router_agent() -> Agent:
    return get_sample_agent("router")


# Registry for legacy references
SAMPLE_AGENTS = {
    "assistant": lambda: get_sample_agent("assistant"),
    "researcher": lambda: get_sample_agent("researcher"),
    "writer": lambda: get_sample_agent("writer"),
    "sre": lambda: get_sample_agent("sre"),
    "analyzer": lambda: get_sample_agent("analyzer"),
    "router": lambda: get_sample_agent("router"),
}
