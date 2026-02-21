"""Backward compatibility — CrewAI LLM adapter moved to crewclaw.provider.crewai."""

# Re-export everything from the new canonical location
from ..provider.crewai import LiteLLMForCrewAI, create_crewai_llm  # noqa: F401

__all__ = ["LiteLLMForCrewAI", "create_crewai_llm"]
