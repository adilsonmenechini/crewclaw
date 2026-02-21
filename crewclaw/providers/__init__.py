"""CrewClaw Provider — LLM and Embedding provider abstractions."""

from .llm import LLM, LiteLLM, create_llm
from .embedder import (
    Embedder,
    OpenAIEmbedder,
    LiteLLMEmbedder,
    SentenceTransformersEmbedder,
    create_embedder,
)
from .crewai import LiteLLMForCrewAI, create_crewai_llm

__all__ = [
    # LLM
    "LLM",
    "LiteLLM",
    "create_llm",
    # Embedders
    "Embedder",
    "OpenAIEmbedder",
    "LiteLLMEmbedder",
    "SentenceTransformersEmbedder",
    "create_embedder",
    # CrewAI adapter
    "LiteLLMForCrewAI",
    "create_crewai_llm",
]
