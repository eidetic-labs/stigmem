"""Test fixtures for the Stigmem reference node."""

from __future__ import annotations

import base64
import json
import sqlite3
import time
import uuid
from collections.abc import Generator
from typing import NamedTuple

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
from stigmem_node.auth import create_api_key
from stigmem_node.db import apply_migrations
from stigmem_node.main import create_app
from stigmem_node.settings import Settings


# ---------------------------------------------------------------------------
# Key helpers
# ---------------------------------------------------------------------------


def generate_keypair() -> tuple[str, str]:
    """Return (pub_b64url, priv_b64url) for a fresh Ed25519 keypair."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption()))
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return pub_b64, priv_b64


def sign_declaration(priv_b64: str, signed_fields: dict) -> str:
    """Sign a PeerDeclaration canonical JSON blob (spec §6.1)."""
    raw = base64.urlsafe_b64decode(priv_b64 + "=" * (-len(priv_b64) % 4))
    privkey = Ed25519PrivateKey.from_private_bytes(raw)
    canonical = json.dumps(signed_fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(privkey.sign(canonical)).decode().rstrip("=")


def make_peer_token(
    priv_b64: str,
    iss: str,
    sub: str,
    scopes: list[str],
    ttl_ms: int = 3_600_000,
    nonce: str | None = None,
    offset_ms: int = 0,
) -> str:
    """Mint an Ed25519-signed peer JWT (spec §3.5)."""
    import jwt

    raw = base64.urlsafe_b64decode(priv_b64 + "=" * (-len(priv_b64) % 4))
    privkey = Ed25519PrivateKey.from_private_bytes(raw)
    now_ms = int(time.time() * 1000) + offset_ms
    payload = {
        "iss": iss,
        "sub": sub,
        "iat": now_ms,
        "exp": now_ms + ttl_ms,
        "nonce": nonce or str(uuid.uuid4()),
        "scopes": scopes,
    }
    return jwt.encode(payload, privkey, algorithm="EdDSA")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Settings patching helpers
# ---------------------------------------------------------------------------

_PATCHABLE_MODULES = [
    "stigmem_node.federation_pull",
    "stigmem_node.peer_token",
    "stigmem_node.federation_ingest",
    "stigmem_node.routes.federation",
    "stigmem_node.decay",
    "stigmem_node.routes.decay",
    "stigmem_node.routes.synthesize",
]


def _get_extra_modules():
    import importlib
    mods = []
    for name in _PATCHABLE_MODULES:
        try:
            mods.append(importlib.import_module(name))
        except ImportError:
            pass
    return mods


def _patch_settings(test_settings: Settings) -> list:
    extra = _get_extra_modules()
    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    wk_mod.settings = test_settings  # type: ignore[assignment]
    for mod in extra:
        if hasattr(mod, "settings"):
            setattr(mod, "settings", test_settings)
    return extra


def _restore_settings(original: Settings, extra: list) -> None:
    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    wk_mod.settings = original  # type: ignore[assignment]
    for mod in extra:
        if hasattr(mod, "settings"):
            setattr(mod, "settings", original)


# ---------------------------------------------------------------------------
# Basic fixtures (Phase 2 compatible)
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path: object) -> str:
    db_file = str(tmp_path) + "/test.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)
    return db_file


@pytest.fixture()
def client(tmp_db: str) -> Generator[TestClient, None, None]:
    """TestClient with auth disabled and a fresh in-process DB."""
    original = settings_module.settings
    test_settings = Settings(db_path=tmp_db, auth_required=False, node_url="http://testnode")
    extra = _patch_settings(test_settings)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    _restore_settings(original, extra)


@pytest.fixture()
def authed_client(tmp_db: str) -> Generator[tuple[TestClient, str], None, None]:
    """TestClient with auth enabled; yields (client, raw_key)."""
    original = settings_module.settings
    test_settings = Settings(db_path=tmp_db, auth_required=True, node_url="http://testnode")
    extra = _patch_settings(test_settings)
    raw_key = create_api_key("agent:test", ["read", "write"])
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c, raw_key
    _restore_settings(original, extra)


# ---------------------------------------------------------------------------
# Federation fixture
# ---------------------------------------------------------------------------


class FedNode(NamedTuple):
    client: TestClient
    db_path: str
    node_id: str
    pub_b64: str
    priv_b64: str
    federate_key: str  # raw API key with read+write+federate permissions
    node_url: str


@pytest.fixture()
def fed_node(tmp_path: object) -> Generator[FedNode, None, None]:
    """A federation-enabled node with a test Ed25519 keypair."""
    import stigmem_node.peer_token as token_mod

    db_file = str(tmp_path) + "/fed_test.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)

    pub_b64, priv_b64 = generate_keypair()
    node_id = "stigmem://test-node-a"
    node_url = "http://test-node-a"

    # Store keys and node_id in node_meta
    conn = sqlite3.connect(db_file)
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('node_id', ?)", (node_id,))
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_pubkey', ?)", (pub_b64,))
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_privkey', ?)", (priv_b64,))
    conn.commit()
    conn.close()

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url=node_url,
        federation_enabled=True,
        federation_pubkey=pub_b64,
        federation_privkey=priv_b64,
    )
    extra = _patch_settings(test_settings)

    # Seed the peer_token cache with this node's keys
    token_mod._cached_pub = pub_b64
    token_mod._cached_priv = priv_b64

    raw_key = create_api_key("agent:test-fed", ["read", "write", "federate"])

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield FedNode(
            client=c,
            db_path=db_file,
            node_id=node_id,
            pub_b64=pub_b64,
            priv_b64=priv_b64,
            federate_key=raw_key,
            node_url=node_url,
        )
    _restore_settings(original, extra)
    token_mod._cached_pub = None
    token_mod._cached_priv = None


@pytest.fixture()
def fed_node_a(tmp_path: object) -> Generator[FedNode, None, None]:
    """Alias for fed_node — test_federation.py uses this name by convention."""
    import stigmem_node.peer_token as token_mod

    db_file = str(tmp_path) + "/fed_test.db"  # type: ignore[operator]
    apply_migrations(db_path=db_file)

    pub_b64, priv_b64 = generate_keypair()
    node_id = "stigmem://test-node-a"
    node_url = "http://test-node-a"

    conn = sqlite3.connect(db_file)
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('node_id', ?)", (node_id,))
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_pubkey', ?)", (pub_b64,))
    conn.execute("INSERT OR REPLACE INTO node_meta (key, value) VALUES ('federation_privkey', ?)", (priv_b64,))
    conn.commit()
    conn.close()

    original = settings_module.settings
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url=node_url,
        federation_enabled=True,
        federation_pubkey=pub_b64,
        federation_privkey=priv_b64,
    )
    extra = _patch_settings(test_settings)

    token_mod._cached_pub = pub_b64
    token_mod._cached_priv = priv_b64

    raw_key = create_api_key("agent:test-fed", ["read", "write", "federate"])

    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield FedNode(
            client=c,
            db_path=db_file,
            node_id=node_id,
            pub_b64=pub_b64,
            priv_b64=priv_b64,
            federate_key=raw_key,
            node_url=node_url,
        )
    _restore_settings(original, extra)
    token_mod._cached_pub = None
    token_mod._cached_priv = None
