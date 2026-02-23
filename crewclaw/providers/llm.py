"""LLM wrapper using LiteLLM for multi-provider support."""

import os
from abc import ABC, abstractmethod
from typing import Any, Literal

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)

def setup_litellm():
    """Ensure litellm is configured with monkeypatches and fallback fixes."""
    try:
        import litellm
        if not hasattr(litellm, "_original_completion"):
            litellm._original_completion = litellm.completion

            def wrapped_completion(*args, **kwargs):
                # Sanitize fallbacks for original LiteLLM call (it expects a list of strings)
                original_fallbacks = kwargs.get("fallbacks", [])
                sanitized_fallbacks = [
                    f["model"] if isinstance(f, dict) else f for f in original_fallbacks
                ]
                kwargs_main = kwargs.copy()
                if original_fallbacks:
                    kwargs_main["fallbacks"] = sanitized_fallbacks

                # Call original completion
                response = litellm._original_completion(*args, **kwargs_main)
                
                # Check for empty response in choices
                if hasattr(response, "choices") and response.choices:
                    content = response.choices[0].message.content
                    if not content or not content.strip():
                        model = kwargs.get("model", "unknown")
                        fallbacks = kwargs.get("fallbacks", [])
                        
                        if fallbacks:
                            next_fallback = fallbacks[0]
                            remaining_fallbacks = fallbacks[1:]
                            
                            # Update kwargs for the next attempt
                            new_kwargs = kwargs.copy()
                            
                            if isinstance(next_fallback, dict):
                                next_model = next_fallback.get("model", "unknown")
                                next_key = next_fallback.get("api_key")
                                if not next_key and "api_key_env" in next_fallback:
                                    next_key = os.environ.get(next_fallback["api_key_env"])
                                
                                if next_key:
                                    new_kwargs["api_key"] = next_key
                                
                                if "base_url" in next_fallback:
                                    new_kwargs["base_url"] = next_fallback["base_url"]
                            else:
                                next_model = next_fallback

                            logger.warning(
                                f"Empty response from {model}. "
                                f"Manually triggering fallback to: {next_model}. "
                                f"Remaining fallbacks: {len(remaining_fallbacks)}"
                            )
                            
                            new_kwargs["model"] = next_model
                            new_kwargs["fallbacks"] = remaining_fallbacks
                            
                            # Recursively call the wrapped version
                            try:
                                return wrapped_completion(*args, **new_kwargs)
                            except Exception as fe:
                                logger.error(f"Fallback attempt failed: {fe}")
                                raise
                        else:
                            logger.error(f"Empty response from {model} and NO fallbacks provided in kwargs.")
                            raise ValueError(f"Empty response from {model}")
                return response

            litellm.completion = wrapped_completion
            litellm.drop_params = True
            logger.debug("Applied litellm monkeypatch for empty response fallbacks")
    except ImportError:
        pass

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
        fallbacks: list[str] | None = None,
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
        
        # Handle structured fallbacks
        raw_fallbacks = fallbacks or config.get("llm.fallbacks", [])
        self.fallbacks = []
        self.fallback_configs = []
        
        import litellm
        
        for fb in raw_fallbacks:
            if isinstance(fb, dict):
                fb_model = fb.get("model")
                self.fallbacks.append(fb_model)
                self.fallback_configs.append(fb)
                
                # Pre-populate litellm's api_key_map if key is provided
                fb_key = fb.get("api_key")
                if not fb_key and "api_key_env" in fb:
                    fb_key = os.environ.get(fb.get("api_key_env"))
                
                if fb_key and fb_model:
                    # LiteLLM uses model as key in api_key_map
                    if not hasattr(litellm, "api_key_map"):
                        litellm.api_key_map = {}
                    litellm.api_key_map[fb_model] = fb_key
            else:
                self.fallbacks.append(fb)
                self.fallback_configs.append({"model": fb})

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
            # First, check for provider-specific environment variables if applicable
            provider_keys = {
                "gemini/": ["GEMINI_API_KEY", "GOOGLE_API_KEY"],
                "anthropic/": ["ANTHROPIC_API_KEY"],
                "openai/": ["OPENAI_API_KEY"],
                "azure/": ["AZURE_API_KEY"],
                "openrouter/": ["OPENROUTER_API_KEY"],
                "ollama/": ["OLLAMA_API_KEY"],
            }
            
            for prefix, env_keys in provider_keys.items():
                if self.model.startswith(prefix):
                    for env_key in env_keys:
                        val = os.environ.get(env_key)
                        if val:
                            self.api_key = val
                            logger.debug(f"Using provider-specific key {env_key} for {self.model}")
                            break
                    if self.api_key:
                        break

            # If still no key, fallback to config/default
            if not self.api_key:
                api_key = llm_config.get("api_key")
                if api_key:
                    self.api_key = api_key
                else:
                    # Check environment from config or default
                    env_key = llm_config.get("api_key_env", "OPENROUTER_API_KEY")
                    self.api_key = os.environ.get(env_key)

        # Base URL for proxies - only apply if not already set
        # and if the current model is the primary model OR doesn't look like a known cloud model
        if not self.base_url:
            config_base_url = llm_config.get("base_url")
            primary_model = llm_config.get("model")
            
            # Simple heuristic: if it's the primary model, use base_url
            # if it starts with gemini/, anthropic/, or azure/, it's likely cloud, so skip global base_url
            is_cloud = any(self.model.startswith(prefix) for prefix in ["gemini/", "anthropic/", "azure/", "openrouter/"])
            
            if config_base_url and (self.model == primary_model or not is_cloud):
                self.base_url = config_base_url
                logger.debug(f"Applying config base_url {self.base_url} to model {self.model}")

    def _get_client(self) -> Any:
        """Get LiteLLM completion function."""
        if self._client is None:
            import litellm
            setup_litellm()
            self._client = litellm
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
            "fallbacks": self.fallbacks,
            **self.extra_params,
            **kwargs,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["base_url"] = self.base_url

        try:
            response = client.completion(**params)
            content = response.choices[0].message.content
            
            # Handle empty or whitespace-only responses as failures to trigger fallbacks
            if not content or not content.strip():
                logger.warning(f"LLM returned empty response for model {self.model}")
                if self.fallbacks:
                    raise ValueError(f"Empty response from {self.model}, triggering fallback")
                return ""
                
            return content
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
            "fallbacks": self.fallbacks,
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
    fallbacks: list[str] | None = None,
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

    if fallbacks is None:
        fallbacks = config.get("llm.fallbacks", [])

    return LiteLLM(model=model, provider=provider, fallbacks=fallbacks, **kwargs)
