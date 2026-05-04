"""Embedding adapter factory — Phase 9 (spec §20 / design memo §2).

Usage::

    from stigmem_node.embedding import get_embedding_model
    model = get_embedding_model(settings)
    vectors = model.embed(["alice memory:role CEO"])
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .base import EmbeddingModel, EmbeddingError, Vector, compose_triple_text, l2_normalize

if TYPE_CHECKING:
    pass

__all__ = [
    "EmbeddingModel",
    "EmbeddingError",
    "Vector",
    "compose_triple_text",
    "l2_normalize",
    "get_embedding_model",
]


def get_embedding_model(settings: object | None = None) -> EmbeddingModel:
    """Return the configured EmbeddingModel instance.

    Reads provider + model_id + dimension from *settings* (or the live
    ``stigmem_node.settings.settings`` singleton when *settings* is None).
    """
    if settings is None:
        from stigmem_node.settings import settings as _s

        settings = _s

    provider: str = getattr(settings, "embed_model_provider", "local")
    model_id: str = getattr(settings, "embed_model_id", "nomic-embed-text-v1.5")
    dimension: int = int(getattr(settings, "embed_dimension", 768))

    if provider == "stub":
        from .stub_adapter import StubEmbeddingModel

        return StubEmbeddingModel(dim=dimension, model_id=model_id)

    if provider == "openai":
        api_key_env: str = getattr(settings, "embed_openai_api_key_env", "OPENAI_API_KEY")
        from .openai_adapter import OpenAIEmbeddingModel

        return OpenAIEmbeddingModel(
            model_id=model_id,
            api_key_env=api_key_env,
            dimension=dimension,
        )

    # default: "local" → Ollama
    ollama_url: str = getattr(settings, "embed_ollama_url", "http://localhost:11434")
    from .local_adapter import OllamaEmbeddingModel

    return OllamaEmbeddingModel(
        model_id=model_id,
        ollama_url=ollama_url,
        dimension=dimension,
    )
