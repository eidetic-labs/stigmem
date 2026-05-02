"""Memory protocol and built-in backends."""
from __future__ import annotations

import uuid
from typing import Any, Protocol, runtime_checkable

from agent_platform.types import MemoryItem, Message


@runtime_checkable
class Memory(Protocol):
    """Structural protocol for memory backends."""

    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str: ...

    async def search(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[MemoryItem]: ...

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]: ...

    async def clear(self, session_id: str) -> None: ...


class InMemoryMemory:
    """Zero-config in-process memory. Suitable for dev and tests."""

    def __init__(self) -> None:
        self._items: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        self._messages: dict[str, list[Message]] = {}

    async def add(
        self,
        content: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> str:
        memory_id = str(uuid.uuid4())
        key = session_id or "_global"
        self._items.setdefault(key, []).append((content, metadata or {}))
        return memory_id

    async def search(
        self,
        query: str,
        limit: int = 10,
        session_id: str | None = None,
    ) -> list[MemoryItem]:
        key = session_id or "_global"
        items = self._items.get(key, [])
        query_lower = query.lower()
        results = [
            MemoryItem(id=str(i), content=content, metadata=meta)
            for i, (content, meta) in enumerate(items)
            if query_lower in content.lower()
        ]
        return results[:limit]

    async def get_messages(
        self,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]:
        return self._messages.get(session_id, [])[-limit:]

    async def append_message(self, session_id: str, message: Message) -> None:
        self._messages.setdefault(session_id, []).append(message)

    async def clear(self, session_id: str) -> None:
        self._items.pop(session_id, None)
        self._messages.pop(session_id, None)
