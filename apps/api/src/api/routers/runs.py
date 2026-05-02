"""Agent run history endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RunSummary(BaseModel):
    id: str
    agent_id: str
    status: str


@router.get("", response_model=list[RunSummary])
async def list_runs() -> list[RunSummary]:
    return []
