"""Crew definitions and helpers."""

from crewai import Agent, Crew, Task, Process

from crewclaw.config import get_config
from crewclaw.config.logging import get_logger

logger = get_logger(__name__)


def create_crew(
    agents: list[Agent],
    tasks: list[Task],
    process: Process = Process.sequential,
    memory: bool = True,
    verbose: bool = True,
    **kwargs,
) -> Crew:
    """Create a Crew with agents and tasks.

    Args:
        agents: List of agents.
        tasks: List of tasks.
        process: Execution process (sequential/hierarchical).
        memory: Enable memory.
        verbose: Verbose output.
        **kwargs: Additional crew kwargs.

    Returns:
        Configured Crew instance.
    """
    config = get_config()

    crew_kwargs = {
        "agents": agents,
        "tasks": tasks,
        "process": process,
        "memory": memory,
        "verbose": verbose,
    }

    # Add memory config if enabled
    if memory:
        crew_kwargs["memory"] = True

    # Add streaming if configured
    if config.get("crew.stream", False):
        crew_kwargs["stream"] = True

    crew_kwargs.update(kwargs)

    crew = Crew(**crew_kwargs)
    logger.info(f"Created crew with {len(agents)} agents, {len(tasks)} tasks")

    return crew


def create_task(
    description: str,
    expected_output: str,
    agent: Agent,
    **kwargs,
) -> Task:
    """Create a task.

    Args:
        description: Task description.
        expected_output: Expected output format.
        agent: Agent to execute task.
        **kwargs: Additional task kwargs.

    Returns:
        Task instance.
    """
    return Task(
        description=description,
        expected_output=expected_output,
        agent=agent,
        **kwargs,
    )
