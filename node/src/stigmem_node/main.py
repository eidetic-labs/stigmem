"""Stigmem reference node — FastAPI application factory and entrypoint."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from .auth import Identity, resolve_identity
from .db import apply_migrations
from .rate_limit import RateLimitMiddleware
from .routes.agent_keys import router as agent_keys_router
from .routes.aliases import router as aliases_router
from .routes.audit import router as audit_router
from .routes.auth import router as auth_router
from .routes.decay import router as decay_router
from .routes.facts import router as facts_router
from .routes.federation import router as federation_router
from .routes.gardens import router as gardens_router
from .routes.intents import router as intents_router
from .routes.lint import router as lint_router
from .routes.resolver import router as resolver_router
from .routes.synthesize import router as synthesize_router
from .routes.wellknown import router as wellknown_router
from .settings import settings

_STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger("stigmem")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        apply_migrations()

        pull_task: asyncio.Task[None] | None = None
        if settings.federation_enabled:
            from .peer_token import init_federation_keys
            from .federation_pull import pull_loop_task

            init_federation_keys()
            pull_task = asyncio.create_task(pull_loop_task())
            logger.info("Stigmem federation enabled — pull interval %ds", settings.federation_pull_interval_s)

        logger.info(
            "Stigmem node ready — db=%s auth=%s federation=%s",
            settings.db_path,
            settings.auth_required,
            "enabled" if settings.federation_enabled else "disabled",
        )
        yield

        if pull_task is not None:
            pull_task.cancel()
            with suppress(asyncio.CancelledError):
                await pull_task

    app = FastAPI(
        title="Stigmem Reference Node",
        version="0.3.0",
        description=(
            "Single-host Stigmem node implementing spec v0.5 — federation handshake and "
            "pull replication (Phase 3). No adapters (Phase 4+)."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(RateLimitMiddleware)

    app.include_router(auth_router)
    app.include_router(agent_keys_router)
    app.include_router(audit_router)
    app.include_router(facts_router)
    app.include_router(gardens_router)
    app.include_router(intents_router)
    app.include_router(federation_router)
    app.include_router(lint_router)
    app.include_router(synthesize_router)
    app.include_router(decay_router)
    app.include_router(aliases_router)
    app.include_router(resolver_router)
    app.include_router(wellknown_router)

    @app.get("/healthz", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/me", tags=["auth"])
    def whoami(identity: Annotated[Identity, Depends(resolve_identity)]) -> dict:
        return {
            "entity_uri": identity.entity_uri,
            "permissions": sorted(identity.permissions),
            "oidc_sub": identity.oidc_sub,
        }

    @app.get("/ui", include_in_schema=False)
    def ui_index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html", media_type="text/html")

    return app


app = create_app()


def run() -> None:
    uvicorn.run(
        "stigmem_node.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
    )


if __name__ == "__main__":
    run()
