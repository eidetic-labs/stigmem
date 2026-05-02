"""Anthropic Claude adapter with prompt caching enabled by default."""

from __future__ import annotations

import os
from typing import Any, AsyncIterator

import anthropic

from agent_platform.llm.base import LLMAdapter, LLMResponse
from agent_platform.types import Message, Role


class AnthropicAdapter(LLMAdapter):
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 8192,
        enable_cache: bool = True,
    ) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model
        self.max_tokens = max_tokens
        self.enable_cache = enable_cache

    def _to_anthropic_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        system: str | None = None
        out: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == Role.SYSTEM:
                system = msg.content
                continue
            entry: dict[str, Any] = {"role": msg.role.value, "content": msg.content}
            out.append(entry)

        return system, out

    async def complete(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        system, msgs = self._to_anthropic_messages(messages)

        # Apply prompt caching to the system prompt when enabled
        system_param: str | list[dict[str, Any]] | anthropic.NotGiven
        if self.enable_cache and system:
            system_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        elif system:
            system_param = system
        else:
            system_param = anthropic.NOT_GIVEN

        response = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_param,
            messages=msgs,
            tools=tools or anthropic.NOT_GIVEN,
            **kwargs,
        )

        return LLMResponse(
            content=response.content[0].text if response.content else "",
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
            stop_reason=response.stop_reason or "end_turn",
        )

    async def stream(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        system, msgs = self._to_anthropic_messages(messages)

        system_param: str | list[dict[str, Any]] | anthropic.NotGiven
        if self.enable_cache and system:
            system_param = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        elif system:
            system_param = system
        else:
            system_param = anthropic.NOT_GIVEN

        async with self._client.messages.stream(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system_param,
            messages=msgs,
            **kwargs,
        ) as stream_ctx:
            async for text in stream_ctx.text_stream:
                yield text
