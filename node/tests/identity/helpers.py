"""Shared helpers for identity route and capability tests."""

from __future__ import annotations

import base64
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import _patch_settings, _restore_settings
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fastapi.testclient import TestClient

import stigmem_node.db as db_mod
import stigmem_node.settings as settings_module
from stigmem_node.identity.manifest import OrgManifest, sign_manifest
from stigmem_node.main import create_app

apply_migrations = db_mod.apply_migrations
Settings = settings_module.Settings


@contextmanager
def patched_test_settings(test_settings: Settings) -> Generator[None, None, None]:
    original = settings_module.settings
    extra = _patch_settings(test_settings)
    try:
        yield
    finally:
        _restore_settings(original, extra)


def gen_keypair() -> tuple[Ed25519PrivateKey, str, str]:
    """Return (private_key_obj, pub_b64url, priv_b64url)."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(
            priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        )
        .decode()
        .rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode()
        .rstrip("=")
    )
    return priv, pub_b64, priv_b64


def make_manifest(
    priv: Ed25519PrivateKey,
    pub_b64: str,
    entity_uri: str = "https://example.org",
    entities: list[str] | None = None,
    key_id: str = "key-1",
    days_valid: int = 365,
) -> OrgManifest:
    now = datetime.now(UTC)
    manifest = OrgManifest(
        entity_uri=entity_uri,
        key_id=key_id,
        public_key=pub_b64,
        issued_at=now.replace(microsecond=0).isoformat(),
        expires_at=(now + timedelta(days=days_valid)).replace(microsecond=0).isoformat(),
        entities=entities if entities is not None else [entity_uri],
    )
    sign_manifest(manifest, priv)
    return manifest


@pytest.fixture()
def identity_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_file = str(tmp_path / "identity_test.db")
    apply_migrations(db_path=db_file)

    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="relaxed",
        tl_backend="off",
    )

    with patched_test_settings(test_settings):
        app = create_app()
        with TestClient(app, raise_server_exceptions=True) as client:
            yield client


@pytest.fixture()
def strict_client(tmp_path: Path) -> Generator[TestClient, None, None]:
    db_file = str(tmp_path / "strict_test.db")
    apply_migrations(db_path=db_file)

    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://testnode",
        trust_mode="strict",
        tl_backend="off",
    )

    with patched_test_settings(test_settings):
        app = create_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client
