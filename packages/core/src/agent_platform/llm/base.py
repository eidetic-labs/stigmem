"""LLM provider adapter protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from agent_platform.types import Message
from pydantic import BaseModel


class LLMResponse(BaseModel):
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    stop_reason: str = "end_turn"
    metadata: dict[str, Any] = {}


class LLMAdapter(ABC):
    """Common interface for all LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        ...
