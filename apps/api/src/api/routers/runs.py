from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class RunSummary(BaseModel):
    id: str
    agent_id: str
    status: str


@router.get("", response_model=list[RunSummary])
async def list_runs() -> list[RunSummary]:
    # Stub: replace with DB query in Phase 2
    return []
