"""Stigmem reference node — FastAPI application factory and entrypoint."""

from __future__ import annotations

import asyncio
import logging
import signal
import ssl
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from typing import Annotated

import uvicorn
from fastapi import Depends, FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse

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
from .routes.graph import router as graph_router
from .routes.identity import router as identity_router
from .routes.intents import router as intents_router
from .routes.lint import router as lint_router
from .routes.quarantine import router as quarantine_router
from .routes.resolver import router as resolver_router
from .routes.cards import router as cards_router
from .routes.recall import router as recall_router
from .routes.subscriptions import router as subscriptions_router
from .routes.instruction import router as instruction_router
from .routes.synthesize import router as synthesize_router
from .routes.admin_audit import router as admin_audit_router
from .routes.cid_admin import router as cid_admin_router
from .routes.tombstones import router as tombstones_router
from .routes.wellknown import router as wellknown_router
from .settings import settings

_STATIC_DIR = Path(__file__).parent / "static"

logger = logging.getLogger("stigmem")


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        apply_migrations()

        if settings.trust_mode == "strict" and not settings.node_private_key:
            raise RuntimeError(
                "STIGMEM_NODE_PRIVATE_KEY must be set when trust_mode=strict"
            )

        if settings.otel_enabled:
            from .tracing import init_tracing
            init_tracing(
                service_name=settings.otel_service_name,
                otlp_endpoint=settings.otel_exporter_otlp_endpoint,
            )

        pull_task: asyncio.Task[None] | None = None
        if settings.federation_enabled:
            from .peer_token import init_federation_keys
            from .federation_pull import pull_loop_task

            init_federation_keys()
            pull_task = asyncio.create_task(pull_loop_task())
            logger.info("Stigmem federation enabled — pull interval %ds", settings.federation_pull_interval_s)

        from .subscription_delivery import sweep_loop as _sub_sweep_loop
        sweep_task: asyncio.Task[None] = asyncio.create_task(_sub_sweep_loop())
        logger.info(
            "Stigmem subscription sweep enabled — interval %ds",
            settings.subscription_delivery_sweep_s,
        )

        logger.info(
            "Stigmem node ready — db=%s auth=%s federation=%s",
            settings.db_path,
            settings.auth_required,
            "enabled" if settings.federation_enabled else "disabled",
        )
        yield

        sweep_task.cancel()
        with suppress(asyncio.CancelledError):
            await sweep_task

        if pull_task is not None:
            pull_task.cancel()
            with suppress(asyncio.CancelledError):
                await pull_task

    app = FastAPI(
        title="Stigmem Reference Node",
        version="1.0.0",
        description=(
            "Reference node implementing the Stigmem v1.0 stable HTTP API, federation, "
            "gardens, recall, subscriptions, audit, and identity surfaces."
        ),
        license_info={"name": "Apache-2.0", "url": "https://www.apache.org/licenses/LICENSE-2.0"},
        lifespan=lifespan,
    )

    app.add_middleware(RateLimitMiddleware)

    if settings.mtls_enabled:
        @app.middleware("http")
        async def mtls_plaintext_guard(request: Request, call_next):  # type: ignore[return]
            """Reject plaintext federation requests when mTLS is configured (§22.1)."""
            if request.url.path.startswith("/v1/federation") and request.url.scheme != "https":
                return JSONResponse(
                    {
                        "error": "mTLS required",
                        "detail": "Federation transport requires mutual TLS (spec §22.1). "
                        "Connect via HTTPS with a valid node certificate.",
                    },
                    status_code=421,
                )
            return await call_next(request)

    app.include_router(admin_audit_router)
    app.include_router(cid_admin_router)
    app.include_router(auth_router)
    app.include_router(agent_keys_router)
    app.include_router(audit_router)
    app.include_router(facts_router)
    app.include_router(gardens_router)
    app.include_router(graph_router)
    app.include_router(identity_router)
    app.include_router(intents_router)
    app.include_router(federation_router)
    app.include_router(quarantine_router)
    app.include_router(lint_router)
    app.include_router(synthesize_router)
    app.include_router(decay_router)
    app.include_router(aliases_router)
    app.include_router(resolver_router)
    app.include_router(cards_router)
    app.include_router(recall_router)
    app.include_router(subscriptions_router)
    app.include_router(tombstones_router)
    app.include_router(wellknown_router)
    app.include_router(instruction_router)

    @app.get("/healthz", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/metrics", include_in_schema=False, tags=["ops"])
    def prometheus_metrics():  # type: ignore[return]
        from .metrics import make_metrics_response
        resp = make_metrics_response()
        if resp is None:
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse("# prometheus_client not installed\n", status_code=200)
        return resp

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
    if not settings.mtls_enabled:
        uvicorn.run(
            "stigmem_node.main:app",
            host=settings.host,
            port=settings.port,
            log_level=settings.log_level,
            reload=False,
        )
        return

    from .tls import cert_watcher_task, reload_tls_cert

    # Let uvicorn build the SSL context from cert/key files, then enforce TLS 1.3
    # floor and mTLS client-cert requirement on the resulting context object.
    config = uvicorn.Config(
        "stigmem_node.main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
        reload=False,
        ssl_certfile=settings.tls_cert_path,
        ssl_keyfile=settings.tls_key_path,
        ssl_ca_certs=settings.tls_ca_bundle or None,
        ssl_cert_reqs=ssl.CERT_REQUIRED,
    )
    config.load()

    if config.ssl:
        config.ssl.minimum_version = ssl.TLSVersion.TLSv1_3
    ssl_ctx = config.ssl

    async def _serve_with_cert_watcher() -> None:
        loop = asyncio.get_running_loop()
        if ssl_ctx is not None:
            loop.add_signal_handler(
                signal.SIGHUP,
                lambda: reload_tls_cert(ssl_ctx),
            )

        server = uvicorn.Server(config)
        watcher_task: asyncio.Task[None] | None = None
        if ssl_ctx is not None:
            watcher_task = asyncio.create_task(cert_watcher_task(ssl_ctx))

        try:
            await server.serve()
        finally:
            if watcher_task is not None:
                watcher_task.cancel()
                with suppress(asyncio.CancelledError):
                    await watcher_task

    config.setup_event_loop()
    asyncio.run(_serve_with_cert_watcher())


if __name__ == "__main__":
    run()
