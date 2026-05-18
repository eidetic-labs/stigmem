"""Cloud opt-in embedding adapter via OpenAI API (design memo §2).

Activated by setting ``STIGMEM_EMBED_MODEL_PROVIDER=openai``.
Requires the OpenAI Python SDK::

    pip install 'stigmem-node[embed-openai]'

The API key is read from the environment variable named by
``STIGMEM_EMBED_OPENAI_API_KEY_ENV`` (default: ``OPENAI_API_KEY``).
"""

from __future__ import annotations

import logging
import os

from .base import EmbeddingError, EmbeddingModel, Vector, l2_normalize

logger = logging.getLogger("stigmem.embed.openai")

_DEFAULT_MODEL = "text-embedding-3-small"
_DEFAULT_DIM = 1536


class OpenAIEmbeddingModel(EmbeddingModel):
    """Embed via OpenAI's embeddings API."""

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        api_key_env: str = "OPENAI_API_KEY",
        dimension: int = _DEFAULT_DIM,
    ) -> None:
        self._model_id = model_id
        self._api_key_env = api_key_env
        self._dimension = dimension

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[Vector]:
        try:
            import openai
        except ImportError as exc:
            raise EmbeddingError(
                "openai package is required for the OpenAI embedding adapter. "
                "Install it with: pip install 'stigmem-node[embed-openai]'"
            ) from exc

        api_key = os.environ.get(self._api_key_env)
        if not api_key:
            logger.debug("OpenAI embedding API key environment variable is unset")
            raise EmbeddingError(
                "OpenAI embedding credentials are not configured. "
                "Set the configured API key environment variable or use a "
                "different embed_model_provider."
            )

        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(model=self._model_id, input=texts)
            vecs = [item.embedding for item in response.data]
        except Exception as exc:
            raise EmbeddingError(f"OpenAI embedding failed: {exc}") from exc

        return [l2_normalize(v) for v in vecs]
