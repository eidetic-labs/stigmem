from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgentSummary(BaseModel):
    id: str
    name: str
    status: str


@router.get("", response_model=list[AgentSummary])
async def list_agents() -> list[AgentSummary]:
    # Stub: replace with DB query in Phase 2
    return []
