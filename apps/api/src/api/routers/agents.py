"""Agent execution endpoints."""
from __future__ import annotations

from agent_platform import Agent, Context, LLMConfig
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class RunRequest(BaseModel):
    message: str
    session_id: str | None = None
    model: str = "claude-sonnet-4-6"
    instructions: str = "You are a helpful assistant."


class RunResponse(BaseModel):
    content: str
    session_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


@router.post("/run", response_model=RunResponse)
async def run_agent(request: RunRequest) -> RunResponse:
    agent = Agent.create(
        name="default",
        instructions=request.instructions,
        llm=LLMConfig(model=request.model),
    )
    ctx = Context(session_id=request.session_id or "default")
    try:
        response = await agent.run(request.message, context=ctx)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    usage = response.usage
    return RunResponse(
        content=response.content,
        session_id=response.session_id,
        input_tokens=usage.input_tokens if usage else 0,
        output_tokens=usage.output_tokens if usage else 0,
        cost_usd=response.cost_usd,
    )
