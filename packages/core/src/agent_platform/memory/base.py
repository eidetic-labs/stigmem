"""Memory protocol and in-process reference implementation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    key: str
    value: Any
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Memory(ABC):
    """Protocol for agent memory backends."""

    @abstractmethod
    async def get(self, key: str) -> MemoryEntry | None:
        ...

    @abstractmethod
    async def set(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> MemoryEntry:
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Semantic or keyword search over stored entries."""
        ...

    @abstractmethod
    async def clear(self) -> None:
        ...


class InMemoryStore(Memory):
    """Simple in-process memory store for development and testing."""

    def __init__(self) -> None:
        self._store: dict[str, MemoryEntry] = {}

    async def get(self, key: str) -> MemoryEntry | None:
        return self._store.get(key)

    async def set(self, key: str, value: Any, metadata: dict[str, Any] | None = None) -> MemoryEntry:
        now = datetime.now(timezone.utc)
        entry = MemoryEntry(
            key=key,
            value=value,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )
        self._store[key] = entry
        return entry

    async def delete(self, key: str) -> bool:
        return self._store.pop(key, None) is not None

    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        # Naive substring search; replace with vector search in production
        q = query.lower()
        results = [
            e for e in self._store.values()
            if q in e.key.lower() or q in str(e.value).lower()
        ]
        return results[:limit]

    async def clear(self) -> None:
        self._store.clear()
