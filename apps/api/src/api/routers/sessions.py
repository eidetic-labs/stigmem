"""Session management endpoints (placeholder)."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class Session(BaseModel):
    session_id: str
    message_count: int = 0


@router.get("/{session_id}", response_model=Session)
async def get_session(session_id: str) -> Session:
    return Session(session_id=session_id)


@router.delete("/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    return {"deleted": session_id}
