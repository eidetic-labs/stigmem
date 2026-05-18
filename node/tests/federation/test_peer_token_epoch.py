from __future__ import annotations

import time
import uuid
from pathlib import Path

import jwt
import pytest

import stigmem_node.db as db_mod
import stigmem_node.federation.peer_token as peer_token_mod
import stigmem_node.settings as settings_module

Settings = settings_module.Settings


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
        token = peer_token_mod.create_peer_token(target_node_id, ["public"], ttl_ms=10_000)
        payload = peer_token_mod.verify_peer_token(
            token,
            peer_token_mod.get_local_pubkey(),
            "peer-self",
        )

    assert payload["sub"] == target_node_id
    assert payload["exp"] - payload["iat"] == 10_000


def test_peer_token_seconds_shaped_expiration_is_rejected(tmp_path: Path) -> None:
    db_file = str(tmp_path / "peer-token-seconds.db")
    db_mod.apply_migrations(db_path=db_file)
    test_settings = Settings(db_path=db_file, auth_required=False, node_url="http://127.0.0.1")

    with _patched_settings(test_settings):
        target_node_id = db_mod.get_or_create_node_id()
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
            peer_token_mod.verify_peer_token(token, peer_token_mod.get_local_pubkey(), "peer-self")

    assert exc.value.kind == "token_expired"
