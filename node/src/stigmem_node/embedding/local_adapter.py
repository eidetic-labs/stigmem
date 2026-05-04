"""Local embedding adapter via Ollama HTTP API (design memo §2).

Default model: ``nomic-embed-text-v1.5`` (768-dim, Apache-2.0, Matryoshka).
Requires a running Ollama instance; install the model with::

    ollama pull nomic-embed-text

Install the optional dependency::

    pip install 'stigmem-node[embed-local]'   # includes httpx
"""

from __future__ import annotations

import logging

from .base import EmbeddingModel, EmbeddingError, Vector, l2_normalize

logger = logging.getLogger("stigmem.embed.local")

_DEFAULT_MODEL = "nomic-embed-text-v1.5"
_DEFAULT_OLLAMA_URL = "http://localhost:11434"


class OllamaEmbeddingModel(EmbeddingModel):
    """Embed via Ollama's ``/api/embeddings`` endpoint."""

    def __init__(
        self,
        model_id: str = _DEFAULT_MODEL,
        ollama_url: str = _DEFAULT_OLLAMA_URL,
        dimension: int = 768,
    ) -> None:
        self._model_id = model_id
        self._ollama_url = ollama_url.rstrip("/")
        self._dimension = dimension

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: list[str]) -> list[Vector]:
        try:
            import httpx
        except ImportError as exc:
            raise EmbeddingError(
                "httpx is required for the Ollama embedding adapter. "
                "It is already a core stigmem-node dependency."
            ) from exc

        results: list[Vector] = []
        url = f"{self._ollama_url}/api/embeddings"
        for text in texts:
            try:
                resp = httpx.post(
                    url,
                    json={"model": self._model_id, "prompt": text},
                    timeout=30.0,
                )
                resp.raise_for_status()
                vec = resp.json()["embedding"]
            except Exception as exc:
                raise EmbeddingError(f"Ollama embedding failed: {exc}") from exc
            results.append(l2_normalize(vec))
        return results
