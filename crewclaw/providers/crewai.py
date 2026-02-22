"""CrewAI-compatible LLM using LiteLLM."""

import os
from typing import Any

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class LiteLLMForCrewAI:
    """LiteLLM wrapper compatible with CrewAI's LLM interface."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        """Initialize LiteLLM for CrewAI.

        Args:
            model: Model name (e.g., "openrouter/google/gemini-2.0-flash-lite").
            api_key: API key.
            base_url: Custom base URL.
            **kwargs: Additional parameters.
        """
        config = get_config()

        self.model = model or config.get("llm.model", "openrouter/google/gemini-2.0-flash-lite")

        # Try to get API key from config or environment
        if api_key:
            self.api_key = api_key
        else:
            # Check config directly first
            self.api_key = config.get("llm.api_key")
            if not self.api_key:
                # Then check environment variable
                env_key = config.get("llm.api_key_env", "OPENROUTER_API_KEY")
                self.api_key = os.environ.get(env_key)

        self.base_url = base_url or config.get("llm.base_url")
        self.extra_params = kwargs

        # Get extra params from config
        self.temperature = config.get("llm.temperature", 0.7)
        self.max_tokens = config.get("llm.max_tokens", 2048)

        self._client: Any = None

    def _get_client(self) -> Any:
        """Get LiteLLM client."""
        if self._client is None:
            try:
                import litellm

                litellm.drop_params = True
                self._client = litellm
            except ImportError:
                raise ImportError("litellm required: pip install litellm")
        return self._client

    def chat(self, messages: list[dict]) -> str:
        """Generate chat completion with retries.

        Args:
            messages: List of message dicts.

        Returns:
            Response text.
        """
        import time
        config = get_config()
        max_retries = config.get("runtime.max_retry_limit", 5)
        client = self._get_client()

        for attempt in range(max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    api_key=self.api_key,
                    base_url=self.base_url,
                    **self.extra_params,
                )

                return response.choices[0].message.content
            except Exception as e:
                if attempt == max_retries:
                    logger.error(f"LLM call failed after {max_retries} retries: {e}")
                    raise

                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s...
                logger.warning(
                    f"LLM call failed: {e}. Retrying in {wait_time}s... "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)

        # Fallback (should not be reached due to raise in loop)
        return ""

    def call(self, messages: list[dict]) -> str:
        """Alias for chat (CrewAI compatibility)."""
        return self.chat(messages)

    @property
    def model_name(self) -> str:
        """Get model name."""
        return self.model


def create_crewai_llm(
    model: str | None = None,
    **kwargs,
) -> LiteLLMForCrewAI:
    """Create CrewAI-compatible LLM.

    Args:
        model: Model name.
        **kwargs: Additional parameters.

    Returns:
        LiteLLMForCrewAI instance.
    """
    return LiteLLMForCrewAI(model=model, **kwargs)
