from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

import jwt
import pytest

import stigmem_node.db as db_mod
import stigmem_node.federation.peer_token as peer_token_mod
import stigmem_node.settings as settings_module

Settings = settings_module.Settings
_PEER_ID = "peer-self"


class _patched_settings:
    def __init__(self, test_settings: Settings) -> None:
        self.test_settings = test_settings
        self.original_settings = settings_module.settings
        self.original_db_settings = db_mod.settings
        self.original_peer_token_settings = peer_token_mod.settings

    def __enter__(self) -> None:
        settings_module.settings = self.test_settings
        db_mod.settings = self.test_settings
        peer_token_mod.settings = self.test_settings
        peer_token_mod._cached_pub = None
        peer_token_mod._cached_priv = None

    def __exit__(self, *_exc: object) -> None:
        settings_module.settings = self.original_settings
        db_mod.settings = self.original_db_settings
        peer_token_mod.settings = self.original_peer_token_settings
        peer_token_mod._cached_pub = None
        peer_token_mod._cached_priv = None


def test_peer_token_roundtrip_uses_epoch_milliseconds(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-ms.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(db_path=db_file, auth_required=False, node_url="http://127.0.0.1")

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, target_node_id, peer_token_mod.get_local_pubkey())
        token = peer_token_mod.create_peer_token(target_node_id, ["public"], ttl_ms=10_000)
        payload = peer_token_mod.verify_peer_token(
            token,
            peer_token_mod.get_local_pubkey(),
            _PEER_ID,
        )

    assert payload["sub"] == target_node_id
    assert payload["exp"] - payload["iat"] == 10_000


def test_peer_token_seconds_shaped_expiration_is_rejected(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-seconds.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(db_path=db_file, auth_required=False, node_url="http://127.0.0.1")

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, target_node_id, peer_token_mod.get_local_pubkey())
        private_key = peer_token_mod._get_privkey_obj()
        now_s = int(time.time())
        token = jwt.encode(
            {
                "iss": target_node_id,
                "sub": target_node_id,
                "iat": now_s,
                "exp": now_s + 3_600,
                "nonce": str(uuid.uuid4()),
                "scopes": ["public"],
            },
            private_key,
            algorithm="EdDSA",
        )

        with pytest.raises(peer_token_mod.TokenError) as exc:
            peer_token_mod.verify_peer_token(token, peer_token_mod.get_local_pubkey(), _PEER_ID)

    assert exc.value.kind == "token_expired"


def test_peer_token_issuer_must_match_peer_row(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-iss.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(db_path=db_file, auth_required=False, node_url="http://127.0.0.1")

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, "stigmem://different-peer", peer_token_mod.get_local_pubkey())
        token = peer_token_mod.create_peer_token(target_node_id, ["public"], ttl_ms=10_000)

        with pytest.raises(peer_token_mod.TokenError) as exc:
            peer_token_mod.verify_peer_token(token, peer_token_mod.get_local_pubkey(), _PEER_ID)

    assert exc.value.kind == "invalid_iss"


def test_peer_token_iat_and_nbf_are_validated(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-claims.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://127.0.0.1",
        peer_token_leeway_s=30,
    )

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, target_node_id, peer_token_mod.get_local_pubkey())
        private_key = peer_token_mod._get_privkey_obj()
        now_ms = int(time.time() * 1000)

        old_iat_token = _encode_peer_token(
            private_key,
            iss=target_node_id,
            sub=target_node_id,
            iat=now_ms - (25 * 60 * 60 * 1000),
            exp=now_ms + 10_000,
        )
        with pytest.raises(peer_token_mod.TokenError) as old_exc:
            peer_token_mod.verify_peer_token(
                old_iat_token, peer_token_mod.get_local_pubkey(), _PEER_ID
            )

        future_iat_token = _encode_peer_token(
            private_key,
            iss=target_node_id,
            sub=target_node_id,
            iat=now_ms + 60_000,
            exp=now_ms + 120_000,
        )
        with pytest.raises(peer_token_mod.TokenError) as future_iat_exc:
            peer_token_mod.verify_peer_token(
                future_iat_token, peer_token_mod.get_local_pubkey(), _PEER_ID
            )

        future_nbf_token = _encode_peer_token(
            private_key,
            iss=target_node_id,
            sub=target_node_id,
            iat=now_ms,
            exp=now_ms + 120_000,
            nbf=now_ms + 60_000,
        )
        with pytest.raises(peer_token_mod.TokenError) as future_nbf_exc:
            peer_token_mod.verify_peer_token(
                future_nbf_token, peer_token_mod.get_local_pubkey(), _PEER_ID
            )

    assert old_exc.value.kind == "iat_too_old"
    assert future_iat_exc.value.kind == "iat_in_future"
    assert future_nbf_exc.value.kind == "nbf_in_future"


def test_peer_token_expiration_uses_configured_leeway(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-leeway.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://127.0.0.1",
        peer_token_leeway_s=30,
    )

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, target_node_id, peer_token_mod.get_local_pubkey())
        private_key = peer_token_mod._get_privkey_obj()
        now_ms = int(time.time() * 1000)
        token = _encode_peer_token(
            private_key,
            iss=target_node_id,
            sub=target_node_id,
            iat=now_ms - 20_000,
            exp=now_ms - 10_000,
        )

        payload = peer_token_mod.verify_peer_token(
            token, peer_token_mod.get_local_pubkey(), _PEER_ID
        )

    assert payload["sub"] == target_node_id


def test_nonce_cache_outlives_token_when_window_is_shorter(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-nonce-ttl.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(
        db_path=db_file,
        auth_required=False,
        node_url="http://127.0.0.1",
        federation_nonce_window_s=10,
    )

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
        _insert_peer(_PEER_ID, target_node_id, peer_token_mod.get_local_pubkey())
        token = peer_token_mod.create_peer_token(target_node_id, ["public"], ttl_ms=60_000)
        payload = peer_token_mod.verify_peer_token(
            token,
            peer_token_mod.get_local_pubkey(),
            _PEER_ID,
        )
        with db_mod.db() as conn:
            row = conn.execute(
                "SELECT expires_at FROM nonce_cache WHERE peer_id = ? AND nonce = ?",
                (_PEER_ID, payload["nonce"]),
            ).fetchone()

    assert row is not None
    nonce_expires_at = datetime.fromisoformat(row["expires_at"])
    assert nonce_expires_at.timestamp() * 1000 >= payload["exp"] - 1_000


def _insert_peer(peer_id: str, node_id: str, pubkey: str) -> None:
    with db_mod.db() as conn:
        conn.execute(
            "INSERT INTO peers "
            "(id, node_id, node_url, federation_pubkey, allowed_scopes, status, "
            "established_at, declaration_sig, signed_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                peer_id,
                node_id,
                "https://peer.example",
                pubkey,
                '["public"]',
                "active",
                datetime.now(UTC).isoformat(),
                "test_sig",
                datetime.now(UTC).isoformat(),
            ),
        )


def _encode_peer_token(
    private_key: object,
    *,
    iss: str,
    sub: str,
    iat: int,
    exp: int,
    nbf: int | None = None,
) -> str:
    payload = {
        "iss": iss,
        "sub": sub,
        "iat": iat,
        "exp": exp,
        "nonce": str(uuid.uuid4()),
        "scopes": ["public"],
    }
    if nbf is not None:
        payload["nbf"] = nbf
    return jwt.encode(payload, private_key, algorithm="EdDSA")
