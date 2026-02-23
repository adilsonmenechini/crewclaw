"""Embedder abstraction for generating vector embeddings."""

import os
from abc import ABC, abstractmethod
from typing import Any

from ..config import get_config
from ..utils.logging import get_logger

logger = get_logger(__name__)


class Embedder(ABC):
    """Abstract base class for embedders."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Embedding dimension."""
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Generate embedding for text.

        Args:
            text: Input text.

        Returns:
            Embedding vector.
        """
        pass

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts.

        Returns:
            List of embedding vectors.
        """
        return [self.embed(text) for text in texts]


class OpenAIEmbedder(Embedder):
    """OpenAI text embedding embedder."""

    def __init__(
        self,
        model: str = "text-embedding-3-small",
        api_key: str | None = None,
    ):
        """Initialize OpenAI embedder.

        Args:
            model: Embedding model name.
            api_key: OpenAI API key. Uses OPENAI_API_KEY env if not provided.
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY.")

        self._client: Any = None
        self._dimension = 1536  # text-embedding-3-small

    @property
    def dimension(self) -> int:
        return self._dimension

    def _get_client(self) -> Any:
        """Get OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError("openai package required. Install with: pip install openai")
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        client = self._get_client()
        response = client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding


class LiteLLMEmbedder(Embedder):
    """Embedder using LiteLLM (supports OpenRouter, Azure, etc.)."""

    # Mapping of provider -> model -> dimension
    DIMENSIONS = {
        "openai": {"text-embedding-3-small": 1536, "text-embedding-3-large": 3072},
        "azure": {"text-embedding-ada-002": 1536},
    }

    def __init__(
        self,
        model: str = "openai/text-embedding-3-small",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """Initialize LiteLLM embedder.

        Args:
            model: Embedding model (e.g., "openai/text-embedding-3-small").
            api_key: API key. Uses env var if not provided.
            base_url: Custom base URL (for proxies).
        """
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._dimension: int | None = None
        self._client: Any = None

        # Set dimension from known models
        for provider, models in self.DIMENSIONS.items():
            if provider in model:
                self._dimension = models.get(model.split("/")[-1], 1536)
                break
        if self._dimension is None:
            self._dimension = 1536  # default

    @property
    def dimension(self) -> int:
        return self._dimension  # type: ignore[return-value]

    def _get_client(self) -> Any:
        """Get LiteLLM client."""
        if self._client is None:
            try:
                import litellm

                self._client = litellm
            except ImportError:
                raise ImportError("litellm required. Install with: pip install litellm")
        return self._client

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        client = self._get_client()

        params = {
            "model": self.model,
            "input": text,
        }

        if self.api_key:
            params["api_key"] = self.api_key
        if self.base_url:
            params["base_url"] = self.base_url

        response = client.embedding(**params)
        return response.data[0].embedding


class SentenceTransformersEmbedder(Embedder):
    """Local embedder using sentence-transformers."""

    def __init__(
        self,
        model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        """Initialize sentence-transformers embedder.

        Args:
            model: Model name from HuggingFace.
        """
        self.model_name = model
        self._model: Any = None
        self._dimension: int | None = None

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            self._load_model()
        return self._dimension  # type: ignore

    def _load_model(self) -> None:
        """Load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded model {self.model_name} with dim {self._dimension}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers required. Install with: pip install sentence-transformers"
                )

    def embed(self, text: str) -> list[float]:
        """Generate embedding for text."""
        self._load_model()
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


def create_embedder() -> Embedder:
    """Create embedder based on configuration.

    Returns:
        Configured embedder instance.
    """
    config = get_config()
    provider = config.get("embedding.provider", "sentence-transformers")

    if provider == "openai":
        model = config.get("embedding.model", "text-embedding-3-small")
        api_key = os.environ.get(config.get("embedding.api_key_env", "OPENAI_API_KEY"))
        return OpenAIEmbedder(model=model, api_key=api_key)

    if provider == "litellm":
        model = config.get("embedding.model", "openai/text-embedding-3-small")
        api_key = os.environ.get(config.get("embedding.api_key_env", "OPENAI_API_KEY"))
        base_url = config.get("embedding.base_url")
        return LiteLLMEmbedder(model=model, api_key=api_key, base_url=base_url)

    model = config.get("embedding.model", "sentence-transformers/all-MiniLM-L6-v2")
    return SentenceTransformersEmbedder(model=model)
