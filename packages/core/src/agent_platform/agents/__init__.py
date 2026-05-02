"""Agent base class and factory."""
from __future__ import annotations

import json
import uuid
from typing import Any, AsyncIterator

import anthropic

from agent_platform.memory import InMemoryMemory, Memory
from agent_platform.tools import FunctionTool, Tool
from agent_platform.types import (
    AgentResponse,
    Context,
    LLMConfig,
    Message,
    Role,
    TokenUsage,
    ToolCall,
    ToolResult,
)


class Agent:
    """Base agent class. Subclass or use Agent.create() for a no-subclass path."""

    name: str = "agent"
    instructions: str = "You are a helpful assistant."
    tools: list[Tool | FunctionTool] = []
    llm: LLMConfig = LLMConfig()
    memory: Memory | None = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Ensure subclass tools list is not shared with the base class
        if "tools" not in cls.__dict__:
            cls.tools = []

    @classmethod
    def create(
        cls,
        name: str,
        instructions: str,
        tools: list[Tool | FunctionTool] | None = None,
        llm: LLMConfig | None = None,
        memory: Memory | None = None,
    ) -> "Agent":
        instance = cls.__new__(cls)
        instance.name = name
        instance.instructions = instructions
        instance.tools = tools or []
        instance.llm = llm or LLMConfig()
        instance.memory = memory or InMemoryMemory()
        return instance

    def _get_memory(self) -> Memory:
        if self.memory is None:
            self.memory = InMemoryMemory()
        return self.memory

    def _build_tool_map(self) -> dict[str, Tool | FunctionTool]:
        return {t.name: t for t in self.tools}

    def _tools_for_api(self) -> list[dict[str, Any]]:
        result = []
        for t in self.tools:
            if isinstance(t, FunctionTool):
                result.append(t.to_api_dict())
            else:
                result.append({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                })
        return result

    async def run(
        self,
        message: str,
        context: Context | None = None,
    ) -> AgentResponse:
        ctx = context or Context(session_id=str(uuid.uuid4()))
        mem = self._get_memory()
        tool_map = self._build_tool_map()

        history = await mem.get_messages(ctx.session_id)
        history.append(Message(role=Role.USER, content=message))

        client = anthropic.AsyncAnthropic()
        all_tool_calls: list[ToolCall] = []
        total_usage = TokenUsage(0, 0)

        while True:
            api_messages = [
                {"role": m.role.value, "content": m.content}
                for m in history
                if m.role in (Role.USER, Role.ASSISTANT)
            ]

            kwargs: dict[str, Any] = {
                "model": self.llm.model,
                "max_tokens": self.llm.max_tokens,
                "system": self.instructions,
                "messages": api_messages,
            }
            if self.tools:
                kwargs["tools"] = self._tools_for_api()

            response = await client.messages.create(**kwargs)

            total_usage.input_tokens += response.usage.input_tokens
            total_usage.output_tokens += response.usage.output_tokens

            if response.stop_reason == "end_turn":
                text_content = next(
                    (b.text for b in response.content if hasattr(b, "text")),
                    "",
                )
                history.append(Message(role=Role.ASSISTANT, content=text_content))
                await mem.append_message(ctx.session_id, history[-2])  # user msg
                await mem.append_message(ctx.session_id, history[-1])  # assistant msg
                return AgentResponse(
                    content=text_content,
                    tool_calls=all_tool_calls,
                    usage=total_usage,
                    session_id=ctx.session_id,
                )

            if response.stop_reason == "tool_use":
                tool_results_content: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    tool_name = block.name
                    tool_args = block.input or {}
                    tool_fn = tool_map.get(tool_name)

                    if tool_fn is None:
                        result = ToolResult(success=False, data=None, error=f"Unknown tool: {tool_name}")
                    else:
                        result = await tool_fn.execute(**tool_args)

                    tc = ToolCall(
                        id=block.id,
                        tool_name=tool_name,
                        args=tool_args,
                        result=result.data,
                        error=result.error,
                    )
                    all_tool_calls.append(tc)

                    tool_results_content.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result.data) if result.success else f"Error: {result.error}",
                    })

                history.append(Message(
                    role=Role.ASSISTANT,
                    content=json.dumps([b.model_dump() for b in response.content]),
                ))
                history.append(Message(
                    role=Role.TOOL,
                    content=json.dumps(tool_results_content),
                ))
                continue

            # Unexpected stop reason
            break

        return AgentResponse(
            content="",
            tool_calls=all_tool_calls,
            usage=total_usage,
            session_id=ctx.session_id,
        )

    async def stream(
        self,
        message: str,
        context: Context | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Streaming execution — yields typed events."""
        ctx = context or Context(session_id=str(uuid.uuid4()))
        client = anthropic.AsyncAnthropic()

        kwargs: dict[str, Any] = {
            "model": self.llm.model,
            "max_tokens": self.llm.max_tokens,
            "system": self.instructions,
            "messages": [{"role": "user", "content": message}],
        }
        if self.tools:
            kwargs["tools"] = self._tools_for_api()

        async with client.messages.stream(**kwargs) as stream:
            async for event in stream:
                if hasattr(event, "type"):
                    if event.type == "content_block_delta":
                        if hasattr(event.delta, "text"):
                            yield {"type": "text_delta", "content": event.delta.text}
                    elif event.type == "content_block_start":
                        if hasattr(event.content_block, "name"):
                            yield {
                                "type": "tool_call",
                                "tool_name": event.content_block.name,
                                "args": {},
                            }
                    elif event.type == "message_stop":
                        yield {"type": "done"}
