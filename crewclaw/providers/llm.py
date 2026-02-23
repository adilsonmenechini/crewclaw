"""LLM wrapper using LiteLLM for multi-provider support."""

import os
from abc import ABC, abstractmethod
from typing import Any, Literal

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)

ProviderType = Literal["openai", "openrouter", "anthropic", "gemini", "azure", "ollama", "auto"]


class LLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def complete(self, messages: list[dict], **kwargs) -> str:
        """Generate completion.

        Args:
            messages: List of message dicts with 'role' and 'content'.
            **kwargs: Additional parameters.

        Returns:
            Completion text.
        """
        pass

    @abstractmethod
    def complete_with_json(self, messages: list[dict], response_schema: dict) -> dict:
        """Generate JSON completion.

        Args:
            messages: List of message dicts.
            response_schema: JSON schema for response.

        Returns:
            Parsed JSON response.
        """
        pass


class LiteLLM(LLM):
    """LiteLLM wrapper for 100+ LLM providers."""

    PROVIDER_MODELS = {
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "openrouter": [
            "openrouter/openai/gpt-4o",
            "openrouter/openai/gpt-4o-mini",
            "openrouter/anthropic/claude-3.5-sonnet",
            "openrouter/google/gemini-2.0-flash",
            "openrouter/google/gemini-2.0-flash-lite",
            "openrouter/deepseek/deepseek-r1",
        ],
        "anthropic": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229"],
        "gemini": [
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
            "gemini-1.5-pro",
            "gemini-1.5-flash",
        ],
        "azure": ["azure/gpt-4o", "azure/gpt-35-turbo"],
        "ollama": ["ollama/llama2", "ollama/mistral"],
    }

    def __init__(
        self,
        model: str | None = None,
        provider: ProviderType = "auto",
        api_key: str | None = None,
        base_url: str | None = None,
        **kwargs,
    ):
        """Initialize LiteLLM.

        Args:
            model: Model name (e.g., "gpt-4o" or "openrouter/google/gemini-2.0-flash").
            provider: Provider name or "auto" to detect from model.
            api_key: API key. Uses env var if not provided.
            base_url: Custom base URL (for proxies).
            **kwargs: Additional LiteLLM parameters.
        """
        config = get_config()

        # Get model from config if not provided
        self.model = model or config.get("llm.model", "openrouter/google/gemini-2.0-flash-lite")
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url
        self.extra_params = kwargs

        # Set API key from config/env
        self._setup_credentials()

        # Validate model
        self._client: Any = None

    def _setup_credentials(self) -> None:
        """Set up credentials from config and environment."""
        config = get_config()
        llm_config = config.get("llm", {})

        # Provider-specific API keys
        if not self.api_key:
            # Check config
            api_key = llm_config.get("api_key")
            if api_key:
                self.api_key = api_key
            else:
                # Check environment
                env_key = llm_config.get("api_key_env", "OPENROUTER_API_KEY")
                self.api_key = os.environ.get(env_key)

        # Base URL for proxies
        if not self.base_url:
            self.base_url = llm_config.get("base_url")

    def _get_client(self) -> Any:
        """Get LiteLLM completion function."""
        if self._client is None:
            try:
                import litellm

                litellm.drop_params = True
                self._client = litellm
            except ImportError:
                raise ImportError("litellm required. Install with: pip install litellm")
        return self._client

    def complete(self, messages: list[dict], **kwargs) -> str:
        """Generate text completion.

        Args:
            messages: List of message dicts.
            **kwargs: Additional parameters.

        Returns:
            Completion text.
        """
        client = self._get_client()

        params = {
            "model": self.model,
            "messages": messages,
            **self.extra_params,
            **kwargs,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["base_url"] = self.base_url

        try:
            response = client.completion(**params)
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM completion failed: {e}")
            raise

    def complete_with_json(self, messages: list[dict], response_schema: dict) -> dict:
        """Generate JSON completion.

        Args:
            messages: List of message dicts.
            response_schema: JSON schema for response.

        Returns:
            Parsed JSON response.
        """
        client = self._get_client()

        import json

        params = {
            "model": self.model,
            "messages": messages,
            "response_format": {
                "type": "json_object",
                "schema": response_schema,
            },
            **self.extra_params,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["base_url"] = self.base_url

        try:
            response = client.completion(**params)
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"JSON completion failed: {e}")
            raise

    def complete_streaming(self, messages: list[dict]):
        """Generate streaming completion.

        Args:
            messages: List of message dicts.

        Yields:
            Chunks of completion text.
        """
        client = self._get_client()

        params = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            **self.extra_params,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["base_url"] = self.base_url

        try:
            response = client.completion(**params)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            raise


def create_llm(
    model: str | None = None,
    provider: ProviderType = "auto",
    **kwargs,
) -> LLM:
    """Create LLM based on configuration.

    Args:
        model: Model name.
        provider: Provider name.
        **kwargs: Additional parameters.

    Returns:
        LLM instance.
    """
    config = get_config()

    # Get from config
    if model is None:
        model = config.get("llm.model")
    if provider == "auto" and model:
        # Detect provider from model name
        if "openrouter" in model:
            provider = "openrouter"
        elif "anthropic" in model or "claude" in model:
            provider = "anthropic"
        elif "gemini" in model:
            provider = "gemini"
        elif model.startswith("azure/"):
            provider = "azure"
        elif "ollama" in model:
            provider = "ollama"

    return LiteLLM(model=model, provider=provider, **kwargs)
