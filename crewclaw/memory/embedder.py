"""Backward compatibility — Embedder abstractions moved to crewclaw.provider.embedder."""

# Re-export everything from the new canonical location
from ..provider.embedder import (  # noqa: F401
    Embedder,
    OpenAIEmbedder,
    LiteLLMEmbedder,
    SentenceTransformersEmbedder,
    create_embedder,
)

__all__ = [
    "Embedder",
    "OpenAIEmbedder",
    "LiteLLMEmbedder",
    "SentenceTransformersEmbedder",
    "create_embedder",
]
