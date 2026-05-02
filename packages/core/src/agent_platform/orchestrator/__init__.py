"""Multi-agent Orchestrator with pluggable routing strategies."""
from __future__ import annotations

import re
from enum import Enum
from typing import Any

import anthropic

from agent_platform.agents import Agent
from agent_platform.types import AgentResponse, Context, LLMConfig


class RoutingStrategy(str, Enum):
    LLM_ROUTER = "llm_router"
    KEYWORD = "keyword"
    ROUND_ROBIN = "round_robin"


class Orchestrator:
    """Routes incoming messages to the appropriate agent."""

    def __init__(
        self,
        agents: dict[str, Agent],
        routing: RoutingStrategy = RoutingStrategy.LLM_ROUTER,
        fallback_agent: str | None = None,
        keyword_rules: dict[str, list[str]] | None = None,
        router_llm: LLMConfig | None = None,
    ) -> None:
        if not agents:
            raise ValueError("Orchestrator requires at least one agent")
        self._agents = agents
        self._routing = routing
        self._fallback = fallback_agent or next(iter(agents))
        self._keyword_rules = keyword_rules or {}
        self._router_llm = router_llm or LLMConfig(model="claude-haiku-4-5-20251001")
        self._rr_index = 0

    async def run(
        self,
        message: str,
        context: Context | None = None,
    ) -> AgentResponse:
        agent_name = await self._route(message)
        agent = self._agents.get(agent_name, self._agents[self._fallback])
        return await agent.run(message, context)

    async def _route(self, message: str) -> str:
        if self._routing == RoutingStrategy.ROUND_ROBIN:
            names = list(self._agents.keys())
            name = names[self._rr_index % len(names)]
            self._rr_index += 1
            return name

        if self._routing == RoutingStrategy.KEYWORD:
            return self._keyword_route(message)

        return await self._llm_route(message)

    def _keyword_route(self, message: str) -> str:
        lower = message.lower()
        for agent_name, keywords in self._keyword_rules.items():
            if any(re.search(kw, lower) for kw in keywords):
                return agent_name
        return self._fallback

    async def _llm_route(self, message: str) -> str:
        agent_names = list(self._agents.keys())
        if len(agent_names) == 1:
            return agent_names[0]

        descriptions = "\n".join(
            f"- {name}: {agent.instructions[:120]}"
            for name, agent in self._agents.items()
        )
        prompt = (
            f"You are a routing assistant. Given a user message, select the most appropriate agent.\n\n"
            f"Available agents:\n{descriptions}\n\n"
            f"User message: {message}\n\n"
            f"Respond with ONLY the agent name (one of: {', '.join(agent_names)})."
        )

        client = anthropic.AsyncAnthropic()
        response = await client.messages.create(
            model=self._router_llm.model,
            max_tokens=20,
            messages=[{"role": "user", "content": prompt}],
        )

        chosen = response.content[0].text.strip().lower()
        for name in agent_names:
            if name.lower() in chosen:
                return name
        return self._fallback
