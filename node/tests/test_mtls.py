"""mTLS federation transport tests — spec §22.1.

Covers:
  - cert rotation mid-flight (load_cert_chain on live context, no drop)
  - rejected handshake (no client cert, wrong CA cert)
  - check_peer_san() URI SAN validation
  - mtls_plaintext_guard middleware returns 421 on http scheme
"""

from __future__ import annotations

import datetime
import socket
import ssl
import threading
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.x509.oid import NameOID

from stigmem_node.tls import (
    build_client_ssl_context,
    build_server_ssl_context,
    check_peer_san,
    reload_tls_cert,
)

# ---------------------------------------------------------------------------
# Cert generation helpers
# ---------------------------------------------------------------------------


def _generate_ca() -> tuple[Ed25519PrivateKey, x509.Certificate]:
    key = Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, None)  # Ed25519 — no hash algorithm
    )
    return key, cert


def _write_node_cert(
    entity_uri: str,
    ca_key: Ed25519PrivateKey,
    ca_cert: x509.Certificate,
    cert_path: Path,
    key_path: Path,
    label: str = "node",
) -> None:
    """Write PEM cert + key signed by ca_key to cert_path / key_path."""
    key = Ed25519PrivateKey.generate()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, label)])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(hours=1))
        .add_extension(
            x509.SubjectAlternativeName([x509.UniformResourceIdentifier(entity_uri)]),
            critical=False,
        )
        .sign(ca_key, None)
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )


# ---------------------------------------------------------------------------
# Minimal echo server for handshake testing
# ---------------------------------------------------------------------------


def _start_echo_server(ssl_ctx: ssl.SSLContext) -> tuple[int, threading.Event]:
    """Start a one-shot TLS echo server in a background thread.

    Returns (port, stop_event).  Set stop_event to shut it down.
    """
    stop_event = threading.Event()

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(5)
    srv.settimeout(0.5)
    port = srv.getsockname()[1]

    def _serve() -> None:
        while not stop_event.is_set():
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            try:
                tls_conn = ssl_ctx.wrap_socket(conn, server_side=True)
                data = tls_conn.recv(256)
                tls_conn.sendall(data)
                tls_conn.close()
            except ssl.SSLError:
                pass
            finally:
                conn.close()
        srv.close()

    threading.Thread(target=_serve, daemon=True).start()
    return port, stop_event


# ---------------------------------------------------------------------------
# Tests: check_peer_san
# ---------------------------------------------------------------------------


def test_check_peer_san_match() -> None:
    peer_cert: dict[str, Any] = {"subjectAltName": [("URI", "stigmem://example.com/org/acme")]}
    assert check_peer_san(peer_cert, "stigmem://example.com/org/acme") is True


def test_check_peer_san_no_match() -> None:
    peer_cert: dict[str, Any] = {"subjectAltName": [("URI", "stigmem://example.com/org/other")]}
    assert check_peer_san(peer_cert, "stigmem://example.com/org/acme") is False


def test_check_peer_san_missing() -> None:
    assert check_peer_san({}, "stigmem://example.com/org/acme") is False


def test_check_peer_san_dns_not_uri() -> None:
    # DNS SAN must not satisfy URI SAN check (different SAN type)
    peer_cert: dict[str, Any] = {"subjectAltName": [("DNS", "stigmem://example.com/org/acme")]}
    assert check_peer_san(peer_cert, "stigmem://example.com/org/acme") is False


# ---------------------------------------------------------------------------
# Tests: cert rotation mid-flight (spec §22.1.3)
# ---------------------------------------------------------------------------


def test_cert_rotation_no_drop(tmp_path: Path) -> None:
    """load_cert_chain() replaces the cert on a live SSLContext without restart.

    Verifies:
    1. Server with cert A accepts mTLS connections.
    2. After reload_tls_cert() with cert B, server accepts new connections.
    3. No ssl.SSLError or server restart occurs during reload.
    """
    ca_key, ca_cert = _generate_ca()
    ca_path = tmp_path / "ca.crt"
    ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))

    # Cert A — initial
    _write_node_cert(
        "stigmem://node-a", ca_key, ca_cert, tmp_path / "a.crt", tmp_path / "a.key", "a"
    )
    # Cert B — replacement
    _write_node_cert(
        "stigmem://node-a", ca_key, ca_cert, tmp_path / "b.crt", tmp_path / "b.key", "b"
    )

    server_ctx = build_server_ssl_context(
        str(tmp_path / "a.crt"), str(tmp_path / "a.key"), str(ca_path)
    )
    port, stop = _start_echo_server(server_ctx)

    # Connection with cert A should succeed
    client_ctx_a = build_client_ssl_context(
        str(tmp_path / "a.crt"), str(tmp_path / "a.key"), str(ca_path)
    )
    raw = socket.create_connection(("127.0.0.1", port), timeout=2)
    tls = client_ctx_a.wrap_socket(raw)
    tls.sendall(b"ping")
    assert tls.recv(4) == b"ping"
    tls.close()

    # Rotate: hot-reload cert B onto the live server context (no restart)
    reload_tls_cert(server_ctx, str(tmp_path / "b.crt"), str(tmp_path / "b.key"))

    # New connection with cert B should also succeed (same CA, new key material)
    client_ctx_b = build_client_ssl_context(
        str(tmp_path / "b.crt"), str(tmp_path / "b.key"), str(ca_path)
    )
    raw2 = socket.create_connection(("127.0.0.1", port), timeout=2)
    tls2 = client_ctx_b.wrap_socket(raw2)
    tls2.sendall(b"pong")
    assert tls2.recv(4) == b"pong"
    tls2.close()

    stop.set()


def test_cert_rotation_invalid_cert_raises(tmp_path: Path) -> None:
    """reload_tls_cert() raises ssl.SSLError on bad cert material (old cert retained)."""
    ca_key, ca_cert = _generate_ca()
    ca_path = tmp_path / "ca.crt"
    ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    _write_node_cert(
        "stigmem://node", ca_key, ca_cert, tmp_path / "node.crt", tmp_path / "node.key"
    )

    server_ctx = build_server_ssl_context(
        str(tmp_path / "node.crt"), str(tmp_path / "node.key"), str(ca_path)
    )

    (tmp_path / "bad.crt").write_text("not-a-cert")
    (tmp_path / "bad.key").write_text("not-a-key")

    with pytest.raises(ssl.SSLError):
        reload_tls_cert(server_ctx, str(tmp_path / "bad.crt"), str(tmp_path / "bad.key"))


# ---------------------------------------------------------------------------
# Tests: rejected handshake (spec §22.1.2.5)
# ---------------------------------------------------------------------------


def test_rejected_handshake_no_client_cert(tmp_path: Path) -> None:
    """TLS handshake fails when client presents no certificate (CERT_REQUIRED)."""
    ca_key, ca_cert = _generate_ca()
    ca_path = tmp_path / "ca.crt"
    ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
    _write_node_cert(
        "stigmem://server", ca_key, ca_cert, tmp_path / "srv.crt", tmp_path / "srv.key", "server"
    )

    server_ctx = build_server_ssl_context(
        str(tmp_path / "srv.crt"), str(tmp_path / "srv.key"), str(ca_path)
    )
    port, stop = _start_echo_server(server_ctx)

    # Client context: verifies server cert but presents no client cert
    no_cert_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    no_cert_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    no_cert_ctx.check_hostname = False
    no_cert_ctx.verify_mode = ssl.CERT_REQUIRED
    no_cert_ctx.load_verify_locations(str(ca_path))
    # Deliberately no load_cert_chain()

    raw = socket.create_connection(("127.0.0.1", port), timeout=2)
    with pytest.raises((ssl.SSLError, OSError)):
        # TLS 1.3: SSLError may arrive during wrap_socket or on the first recv
        tls = no_cert_ctx.wrap_socket(raw)
        tls.recv(1)

    stop.set()


def test_rejected_handshake_wrong_ca(tmp_path: Path) -> None:
    """Client cert signed by an untrusted CA is rejected at handshake."""
    # Server trusts its own CA only
    ca_key_s, ca_cert_s = _generate_ca()
    ca_path_s = tmp_path / "ca_s.crt"
    ca_path_s.write_bytes(ca_cert_s.public_bytes(serialization.Encoding.PEM))
    _write_node_cert(
        "stigmem://server",
        ca_key_s,
        ca_cert_s,
        tmp_path / "srv.crt",
        tmp_path / "srv.key",
        "server",
    )

    # Rogue CA — not trusted by server
    ca_key_r, ca_cert_r = _generate_ca()
    ca_path_r = tmp_path / "ca_r.crt"
    ca_path_r.write_bytes(ca_cert_r.public_bytes(serialization.Encoding.PEM))
    _write_node_cert(
        "stigmem://rogue",
        ca_key_r,
        ca_cert_r,
        tmp_path / "rogue.crt",
        tmp_path / "rogue.key",
        "rogue",
    )

    server_ctx = build_server_ssl_context(
        str(tmp_path / "srv.crt"), str(tmp_path / "srv.key"), str(ca_path_s)
    )
    port, stop = _start_echo_server(server_ctx)

    # Client presents rogue cert; verifies server against server CA
    rogue_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    rogue_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    rogue_ctx.check_hostname = False
    rogue_ctx.verify_mode = ssl.CERT_REQUIRED
    rogue_ctx.load_cert_chain(str(tmp_path / "rogue.crt"), str(tmp_path / "rogue.key"))
    rogue_ctx.load_verify_locations(str(ca_path_s))

    raw = socket.create_connection(("127.0.0.1", port), timeout=2)
    with pytest.raises((ssl.SSLError, OSError)):
        # TLS 1.3: alert may arrive during wrap_socket or on first recv
        tls = rogue_ctx.wrap_socket(raw)
        tls.recv(1)

    stop.set()


# ---------------------------------------------------------------------------
# Tests: mtls_plaintext_guard middleware
# ---------------------------------------------------------------------------


def test_mtls_plaintext_guard_returns_421(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Federation routes return 421 when mTLS is configured and request is http."""
    from fastapi.testclient import TestClient

    import stigmem_node.main as main_mod
    import stigmem_node.settings as settings_module

    # Write placeholder files so mtls_enabled property returns True
    (tmp_path / "node.crt").write_text("placeholder")
    (tmp_path / "node.key").write_text("placeholder")
    (tmp_path / "ca.crt").write_text("placeholder")

    fake_settings = settings_module.Settings(
        tls_cert_path=str(tmp_path / "node.crt"),
        tls_key_path=str(tmp_path / "node.key"),
        tls_ca_bundle=str(tmp_path / "ca.crt"),
    )
    monkeypatch.setattr(settings_module, "settings", fake_settings)
    monkeypatch.setattr(main_mod, "settings", fake_settings)

    app = main_mod.create_app()
    client = TestClient(app, raise_server_exceptions=False)

    resp = client.get("/v1/federation/peers")
    assert resp.status_code == 421
    body = resp.json()
    assert body["error"] == "mTLS required"


def test_non_federation_routes_bypass_mtls_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """/healthz and other non-federation routes are not blocked by the guard."""
    from fastapi.testclient import TestClient

    import stigmem_node.main as main_mod
    import stigmem_node.settings as settings_module

    (tmp_path / "node.crt").write_text("placeholder")
    (tmp_path / "node.key").write_text("placeholder")
    (tmp_path / "ca.crt").write_text("placeholder")

    fake_settings = settings_module.Settings(
        tls_cert_path=str(tmp_path / "node.crt"),
        tls_key_path=str(tmp_path / "node.key"),
        tls_ca_bundle=str(tmp_path / "ca.crt"),
    )
    monkeypatch.setattr(settings_module, "settings", fake_settings)
    monkeypatch.setattr(main_mod, "settings", fake_settings)

    app = main_mod.create_app()
    client = TestClient(app, raise_server_exceptions=False)

    assert client.get("/healthz").status_code == 200


# ---------------------------------------------------------------------------
# Regression: HIGH-1 — ca_bundle required when mTLS enabled (§22.1.2.2)
# ---------------------------------------------------------------------------


def test_settings_requires_ca_bundle_when_mtls_enabled(tmp_path: Path) -> None:
    """Settings raises ValueError when cert+key are set but ca_bundle is empty."""
    import pydantic

    from stigmem_node.settings import Settings

    (tmp_path / "node.crt").write_text("placeholder")
    (tmp_path / "node.key").write_text("placeholder")

    with pytest.raises((ValueError, pydantic.ValidationError)):
        Settings(
            tls_cert_path=str(tmp_path / "node.crt"),
            tls_key_path=str(tmp_path / "node.key"),
            tls_ca_bundle="",
        )


def test_settings_accepts_mtls_with_ca_bundle(tmp_path: Path) -> None:
    """Settings succeeds when all three mTLS fields are set."""
    from stigmem_node.settings import Settings

    (tmp_path / "node.crt").write_text("placeholder")
    (tmp_path / "node.key").write_text("placeholder")
    (tmp_path / "ca.crt").write_text("placeholder")

    s = Settings(
        tls_cert_path=str(tmp_path / "node.crt"),
        tls_key_path=str(tmp_path / "node.key"),
        tls_ca_bundle=str(tmp_path / "ca.crt"),
    )
    assert s.mtls_enabled is True


# ---------------------------------------------------------------------------
# Regression: CRITICAL-1 — server-side SAN enforcement (_require_peer_token)
# ---------------------------------------------------------------------------


def test_get_mtls_peer_cert_no_transport() -> None:
    """_get_mtls_peer_cert returns empty dict when no transport in scope."""
    from starlette.requests import Request

    from stigmem_node.routes.federation import _get_mtls_peer_cert

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 8765),
    }
    req = Request(scope)
    assert _get_mtls_peer_cert(req) == {}


def test_get_mtls_peer_cert_ssl_transport() -> None:
    """_get_mtls_peer_cert extracts peer cert dict from mock SSL transport."""
    from starlette.requests import Request

    from stigmem_node.routes.federation import _get_mtls_peer_cert

    mock_cert = {"subjectAltName": [("URI", "stigmem://example.com/org/peer")]}
    mock_ssl = MagicMock()
    mock_ssl.getpeercert.return_value = mock_cert
    mock_transport = MagicMock()
    mock_transport.get_extra_info.return_value = mock_ssl

    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "server": ("localhost", 8765),
        "transport": mock_transport,
    }
    req = Request(scope)
    assert _get_mtls_peer_cert(req) == mock_cert


# ---------------------------------------------------------------------------
# Regression: CRITICAL-2 — client-side SAN enforcement (pull_from_peer_once)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pull_from_peer_san_mismatch_returns_old_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pull_from_peer_once returns old cursor (fail-closed) when SAN does not match."""
    import stigmem_node.federation_pull as pull_mod

    # Simulate mtls_enabled = True
    fake_settings = MagicMock()
    fake_settings.mtls_enabled = True
    monkeypatch.setattr(pull_mod, "settings", fake_settings)

    # Mock ssl_object returning a cert with wrong SAN
    mock_ssl = MagicMock()
    mock_ssl.getpeercert.return_value = {
        "subjectAltName": [("URI", "stigmem://attacker.example/org/evil")]
    }

    # Build a fake 200 httpx Response with ssl_object extension
    import httpx

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.extensions = {"ssl_object": mock_ssl}

    # Mock the client.get to return mock_resp
    mock_client = MagicMock()
    mock_client.get = MagicMock(return_value=mock_resp)

    # Make client.get awaitable

    async def _fake_get(*args, **kwargs):
        return mock_resp

    mock_client.get = _fake_get

    # Also mock write_audit_log and create_peer_token
    monkeypatch.setattr(pull_mod, "write_audit_log", MagicMock())
    monkeypatch.setattr(pull_mod, "create_peer_token", lambda *a, **kw: "tok")

    peer = {
        "node_id": "stigmem://legitimate.example/org/peer",
        "node_url": "https://legitimate.example",
        "allowed_scopes": '["global"]',
    }
    old_cursor = "cursor-abc"

    result = await pull_mod.pull_from_peer_once(peer, mock_client, old_cursor)
    assert result == old_cursor, "SAN mismatch must return old cursor (fail-closed)"
