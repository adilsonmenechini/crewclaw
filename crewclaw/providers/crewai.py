"""CrewAI-compatible LLM using LiteLLM."""

import os
from typing import Any

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


def LiteLLMForCrewAI(
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs,
):
    """Factory for creating CrewAI-compatible LLM using LiteLLM.

    Uses crewai.LLM internally for maximum compatibility with newer versions.
    """
    import litellm
    from crewai import LLM

    # Enable verbose logging for debugging
    os.environ["LITELLM_LOG"] = "DEBUG"
    litellm.drop_params = True

    config = get_config()

    model_str: str = str(
        model or config.get("llm.model", "openrouter/google/gemini-2.0-flash-lite")
    )

    # Try to get API key
    if not api_key:
        api_key = config.get("llm.api_key")
        if not api_key:
            env_key = config.get("llm.api_key_env", "OPENROUTER_API_KEY")
            api_key = os.environ.get(env_key)

    base_url = base_url or config.get("llm.base_url")

    temperature = config.get("llm.temperature", 0.7)
    max_tokens = config.get("llm.max_tokens", 4096)

    # Note: LiteLLM provider in CrewAI v0.60+ expects the model string
    # and handles base_url/api_key if passed correctly.
    return LLM(
        model=model_str,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def create_crewai_llm(
    model: str | None = None,
    **kwargs,
) -> Any:
    """Create CrewAI-compatible LLM."""
    return LiteLLMForCrewAI(model=model, **kwargs)
