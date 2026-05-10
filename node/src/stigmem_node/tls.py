"""mTLS support for federation transport (spec §22.1).

Builds and manages SSL contexts for server (uvicorn) and client (httpx)
federation connections.  Hot-reload is achieved by calling load_cert_chain()
on the existing SSLContext reference — in-flight connections are unaffected
because TLS state is per-connection, not per-context.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from pathlib import Path
from typing import Any

from .settings import settings

logger = logging.getLogger("stigmem.tls")

# TLS 1.3 cipher suites mandated by spec §22.1.2.3.
# Passed to uvicorn's ssl_ciphers for the TLS 1.2 cipher list (kept empty to
# allow only TLS 1.3); TLS 1.3 suites are enforced by setting minimum_version
# on the SSLContext after creation.
_TLS13_SUITE_NAMES = (
    "TLS_AES_256_GCM_SHA384",
    "TLS_AES_128_GCM_SHA256",
    "TLS_CHACHA20_POLY1305_SHA256",
)

# Colon-separated string for OpenSSL cipher list APIs.
TLS13_CIPHERS = ":".join(_TLS13_SUITE_NAMES)


def build_server_ssl_context(
    cert_path: str,
    key_path: str,
    ca_bundle: str,
) -> ssl.SSLContext:
    """Create a TLS 1.3 server SSLContext that requires a client certificate.

    The returned context can be mutated in-place via load_cert_chain() for
    zero-downtime certificate rotation.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.check_hostname = False  # SAN verified by check_peer_san() at app layer
    ctx.load_cert_chain(cert_path, key_path)
    if ca_bundle:
        ctx.load_verify_locations(ca_bundle)
    return ctx


def build_client_ssl_context(
    cert_path: str,
    key_path: str,
    ca_bundle: str,
) -> ssl.SSLContext:
    """Create a TLS 1.3 client SSLContext that presents the node's cert.

    Pass the returned context as ``verify=ctx`` to httpx.AsyncClient; httpx
    will present the loaded client cert during the TLS handshake.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.check_hostname = False  # SAN verified by check_peer_san() at app layer
    ctx.verify_mode = ssl.CERT_REQUIRED
    ctx.load_cert_chain(cert_path, key_path)
    if ca_bundle:
        ctx.load_verify_locations(ca_bundle)
    return ctx


def reload_tls_cert(
    ctx: ssl.SSLContext,
    cert_path: str | None = None,
    key_path: str | None = None,
) -> None:
    """Hot-reload the certificate on *ctx* without restarting the server.

    Existing TLS connections are unaffected; new handshakes pick up the new
    cert immediately.  Raises ssl.SSLError if the new cert/key pair is invalid.
    """
    cert = cert_path or settings.tls_cert_path
    key = key_path or settings.tls_key_path
    ctx.load_cert_chain(cert, key)
    logger.info("TLS certificate reloaded from %s", cert)


def check_peer_san(peer_cert: dict[str, Any], expected_entity_uri: str) -> bool:
    """Return True iff the peer's certificate contains entity_uri as a URI SAN.

    peer_cert is the dict returned by ssl.SSLSocket.getpeercert().
    Called after a successful TLS handshake to enforce §22.1.2.4.
    """
    for kind, value in peer_cert.get("subjectAltName", ()):
        if kind == "URI" and value == expected_entity_uri:
            return True
    return False


async def cert_watcher_task(ctx: ssl.SSLContext, poll_interval: float = 5.0) -> None:
    """Async task: watch the cert file for changes and hot-reload on mtime delta.

    Intended to run as an asyncio task alongside the uvicorn server.  Cancels
    cleanly when the parent lifespan shuts down.
    """
    path = Path(settings.tls_cert_path)
    try:
        last_mtime = path.stat().st_mtime
    except OSError:
        last_mtime = 0.0

    while True:
        await asyncio.sleep(poll_interval)
        try:
            mtime = path.stat().st_mtime
            if mtime != last_mtime:
                logger.info("TLS cert file changed — reloading")
                try:
                    reload_tls_cert(ctx)
                    last_mtime = mtime
                except ssl.SSLError:
                    logger.exception("TLS cert reload failed — keeping old cert")
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Unexpected error in cert watcher")
