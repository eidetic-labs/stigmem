"""Muninn reference node — FastAPI application factory and entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI

from .db import apply_migrations
from .routes.facts import router as facts_router
from .routes.wellknown import router as wellknown_router
from .settings import settings

logger = logging.getLogger("muninn")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        apply_migrations()
        logger.info("Muninn node ready — db=%s auth=%s", settings.db_path, settings.auth_required)
        yield

    app = FastAPI(
        title="Muninn Reference Node",
        version="0.2.0",
        description=(
            "Single-host Muninn node implementing spec v0.3. "
            "No federation (Phase 3). No adapters (Phase 4)."
        ),
        lifespan=lifespan,
    )

    app.include_router(facts_router)
    app.include_router(wellknown_router)

    @app.get("/healthz", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "muninn_node.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
