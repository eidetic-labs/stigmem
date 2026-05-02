"""FastAPI application entrypoint."""

from __future__ import annotations

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import agents, health, runs

logger = structlog.get_logger()


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Platform API",
        version="0.1.0",
        description="Open-source AI agent platform REST API",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Tighten in production via settings
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, tags=["health"])
    app.include_router(agents.router, prefix="/v1/agents", tags=["agents"])
    app.include_router(runs.router, prefix="/v1/runs", tags=["runs"])

    @app.on_event("startup")
    async def startup() -> None:
        logger.info("api.startup", version="0.1.0")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        logger.info("api.shutdown")

    return app


app = create_app()
