"""Deterministic stub EmbeddingModel — for tests and offline development.

Produces reproducible L2-normalised vectors derived from text hashes.
Never requires external dependencies.
"""

from __future__ import annotations

import hashlib

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
            raw: list[float] = []
            counter = 0
            while len(raw) < self._dim:
                digest = hashlib.sha256(f"{text}:{counter}".encode()).digest()
                counter += 1
                for offset in range(0, len(digest), 4):
                    chunk = digest[offset : offset + 4]
                    if len(chunk) < 4:
                        continue
                    unit = int.from_bytes(chunk, "big") / 0xFFFFFFFF
                    raw.append((unit * 2.0) - 1.0)
                    if len(raw) == self._dim:
                        break
            result.append(l2_normalize(raw))
        return result
