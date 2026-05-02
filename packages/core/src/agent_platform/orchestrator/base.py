"""Orchestrator — coordinates multiple agents for complex multi-step tasks."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from agent_platform.agents.base import Agent, AgentResult
from agent_platform.types import Context


class OrchestratorConfig(BaseModel):
    max_agents: int = 10
    max_total_iterations: int = 100
    metadata: dict[str, Any] = {}


class Orchestrator:
    """Routes tasks to agents and aggregates results."""

    def __init__(self, config: OrchestratorConfig | None = None) -> None:
        self.config = config or OrchestratorConfig()
        self._agents: dict[str, Agent] = {}

    def register(self, name: str, agent: Agent) -> None:
        if len(self._agents) >= self.config.max_agents:
            raise ValueError(f"Max agent limit ({self.config.max_agents}) reached")
        self._agents[name] = agent

    def get(self, name: str) -> Agent | None:
        return self._agents.get(name)

    async def run(
        self,
        agent_name: str,
        user_input: str,
        **kwargs: Any,
    ) -> AgentResult:
        agent = self._agents.get(agent_name)
        if agent is None:
            raise KeyError(f"Agent '{agent_name}' not registered")
        return await agent.run(user_input, **kwargs)

    async def run_pipeline(
        self,
        steps: list[tuple[str, str]],
        initial_input: str,
    ) -> list[AgentResult]:
        """Run agents in sequence, passing each result as input to the next."""
        results: list[AgentResult] = []
        current_input = initial_input

        for agent_name, prompt_template in steps:
            formatted = prompt_template.format(input=current_input)
            result = await self.run(agent_name, formatted)
            results.append(result)
            current_input = result.output

        return results
