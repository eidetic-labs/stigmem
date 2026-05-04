"""EmbeddingModel abstract base — Phase 9 (spec §20 / design memo §2)."""

from __future__ import annotations

from abc import ABC, abstractmethod


Vector = list[float]


class EmbeddingModel(ABC):
    """Swappable embedding-model adapter.

    All implementations MUST normalize output vectors to unit length (L2) so
    that cosine similarity reduces to a dot product in sqlite-vec (design memo §2).
    """

    @property
    @abstractmethod
    def model_id(self) -> str:
        """Stable identifier for this model, e.g. ``'nomic-embed-text-v1.5'``."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Output vector dimensionality."""
        ...

    @abstractmethod
    def embed(self, texts: list[str]) -> list[Vector]:
        """Embed *texts* and return L2-normalised vectors.

        Returns one vector per input text, in the same order.
        Raises ``EmbeddingError`` on unrecoverable failures.
        """
        ...


class EmbeddingError(RuntimeError):
    """Raised when embedding fails unrecoverably (network error, API quota, etc.)."""


def l2_normalize(vec: list[float]) -> list[float]:
    """Return L2-normalised copy of *vec*. Zero vector returned unchanged."""
    import math

    norm = math.sqrt(sum(x * x for x in vec))
    if norm == 0.0:
        return vec
    return [x / norm for x in vec]


def compose_triple_text(entity: str, relation: str, value_type: str, value_v: str) -> str:
    """Compose the canonical text to embed for a fact triple (design memo §2 Option B).

    For ref-typed values, uses the last path segment of the URI as the display
    name to improve semantic alignment.
    """
    if value_type == "ref" and value_v:
        display_v = value_v.rstrip("/").rsplit("/", 1)[-1]
    else:
        display_v = str(value_v) if value_v is not None else ""

    entity_display = entity.rstrip("/").rsplit("/", 1)[-1]
    return f"{entity_display} {relation} {display_v}"
