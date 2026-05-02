"""Agent base class and protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from agent_platform.memory.base import InMemoryStore, Memory
from agent_platform.tools.base import Tool, ToolRegistry
from agent_platform.types import Context, Message, Role


class AgentConfig(BaseModel):
    agent_id: str
    system_prompt: str = ""
    model: str = "claude-sonnet-4-6"
    max_iterations: int = 20
    temperature: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    output: str
    messages: list[Message]
    iterations: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Agent(ABC):
    """Abstract base class for all platform agents."""

    def __init__(
        self,
        config: AgentConfig,
        tools: list[Tool] | None = None,
        memory: Memory | None = None,
    ) -> None:
        self.config = config
        self.registry = ToolRegistry()
        self.memory = memory or InMemoryStore()

        for t in (tools or []):
            self.registry.register(t)

    def add_tool(self, t: Tool) -> None:
        self.registry.register(t)

    def _make_context(self, user_input: str) -> Context:
        ctx = Context(
            agent_id=self.config.agent_id,
            max_iterations=self.config.max_iterations,
        )
        if self.config.system_prompt:
            ctx.add_message(Role.SYSTEM, self.config.system_prompt)
        ctx.add_message(Role.USER, user_input)
        return ctx

    @abstractmethod
    async def run(self, user_input: str, **kwargs: Any) -> AgentResult:
        """Execute the agent for a single turn."""
        ...

    @abstractmethod
    async def stream(self, user_input: str, **kwargs: Any) -> Any:
        """Stream agent output tokens as they arrive."""
        ...
