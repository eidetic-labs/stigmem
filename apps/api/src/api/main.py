"""FastAPI application entry point."""
from __future__ import annotations

import structlog
from api.routers import agents, health, runs, sessions
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = structlog.get_logger()

app = FastAPI(
    title="AI Platform API",
    description="Open-source AI platform — agent execution, compliance, integrations",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(runs.router, prefix="/api/v1/runs", tags=["runs"])
app.include_router(sessions.router, prefix="/api/v1/sessions", tags=["sessions"])


@app.on_event("startup")
async def startup() -> None:
    logger.info("AI Platform API starting up")


@app.on_event("shutdown")
async def shutdown() -> None:
    logger.info("AI Platform API shutting down")
