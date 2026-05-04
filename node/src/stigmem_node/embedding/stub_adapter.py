"""Deterministic stub EmbeddingModel — for tests and offline development.

Produces random-but-reproducible L2-normalised vectors seeded from text hash.
Never requires external dependencies.
"""

from __future__ import annotations

import hashlib
import math
import random

from .base import EmbeddingModel, Vector, l2_normalize

_DEFAULT_STUB_DIM = 4  # minimal dimension; tests override via constructor


class StubEmbeddingModel(EmbeddingModel):
    """Test / offline stub that returns deterministic unit vectors."""

    def __init__(self, dim: int = _DEFAULT_STUB_DIM, model_id: str = "stub") -> None:
        self._dim = dim
        self._model_id = model_id

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, texts: list[str]) -> list[Vector]:
        result: list[Vector] = []
        for text in texts:
            digest = hashlib.sha256(text.encode()).digest()
            seed = int.from_bytes(digest[:8], "big")
            rng = random.Random(seed)  # nosec B311 — deterministic test stub; seed is a SHA-256 digest, not a secret
            raw = [rng.gauss(0, 1) for _ in range(self._dim)]
            result.append(l2_normalize(raw))
        return result
