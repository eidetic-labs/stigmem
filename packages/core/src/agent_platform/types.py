"""Shared types used across all agent_platform primitives."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class Role(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class Message:
    role: Role
    content: str
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


@dataclass
class Context:
    session_id: str
    user_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ToolCall:
    id: str
    tool_name: str
    args: dict[str, Any]
    result: Any = None
    error: str | None = None


@dataclass
class AgentResponse:
    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: TokenUsage | None = None
    cost_usd: float = 0.0
    trace_id: str | None = None
    session_id: str | None = None


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: str | None = None


@dataclass
class MemoryItem:
    id: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float | None = None


@dataclass
class LLMConfig:
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-6"
    temperature: float = 0.0
    max_tokens: int = 4096
    system_prompt: str | None = None


JsonSchema = dict[str, Any]
