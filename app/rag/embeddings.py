"""
Local embedding model provider using Ollama.

The same embedding model is used for indexing and querying.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_ollama import OllamaEmbeddings

from app.config import get_settings


@lru_cache(maxsize=1)
def get_embeddings() -> OllamaEmbeddings:
    """Return a cached local Ollama embeddings instance."""

    settings = get_settings()

    return OllamaEmbeddings(
        model=settings.openai_embedding_model,
        base_url="http://localhost:11434",
    )