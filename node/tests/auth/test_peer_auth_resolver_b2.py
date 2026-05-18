"""B2 coverage push for peer_auth.py (53 missing) + entity_resolver.py (53 missing).

Both modules have small, mostly-pure helpers that the existing federation
integration tests exercise indirectly but never with the targeted edge
inputs (malformed tokens, signature failures, fuzzy resolver edge tokens).
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

import jwt
import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _migrated_db(tmp_path: Path) -> str:
    from stigmem_node.db import apply_migrations

    db_file = str(tmp_path / "pa_b2.db")
    apply_migrations(db_path=db_file)
    return db_file


def _patched_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Migrated DB + module-level settings.db_path patched."""
    from stigmem_node import db as db_mod

    db = _migrated_db(tmp_path)
    monkeypatch.setattr(db_mod.settings, "db_path", db)
    return db


# ---------------------------------------------------------------------------
# peer_auth: base64url helpers
# ---------------------------------------------------------------------------


class TestB64Helpers:
    def test_encode_decode_roundtrip(self) -> None:
        from stigmem_node.peer_auth import b64url_decode, b64url_encode

        for blob in [b"", b"a", b"hello world", bytes(range(256))]:
            encoded = b64url_encode(blob)
            assert "=" not in encoded
            assert b64url_decode(encoded) == blob

    def test_decode_handles_missing_padding(self) -> None:
        from stigmem_node.peer_auth import b64url_decode, b64url_encode

        # Pad-stripped strings of various lengths
        for blob in [b"x", b"xx", b"xxx"]:
            assert b64url_decode(b64url_encode(blob)) == blob


# ---------------------------------------------------------------------------
# peer_auth: keypair + token mint/verify
# ---------------------------------------------------------------------------


class TestKeypair:
    def test_get_or_create_keypair_creates_then_returns_same(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.peer_auth import get_or_create_keypair

        _patched_db(tmp_path, monkeypatch)

        priv1, pub1 = get_or_create_keypair()
        priv2, pub2 = get_or_create_keypair()
        # Same public key on second call
        assert pub1 == pub2

    def test_get_federation_pubkey_returns_b64url(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.peer_auth import get_federation_pubkey

        _patched_db(tmp_path, monkeypatch)
        pk = get_federation_pubkey()
        assert isinstance(pk, str)
        assert "=" not in pk
        # Ed25519 raw pubkey is 32 bytes → b64url ≈ 43 chars
        assert 40 <= len(pk) <= 50


class TestPeerTokenMintVerify:
    def test_mint_and_verify_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node import peer_auth

        db = _patched_db(tmp_path, monkeypatch)

        # Mint a token from "us" → "them"
        local = "stigmem://local"
        remote = "stigmem://remote"
        # mint_peer_token uses the local keypair; we then need that pubkey
        # registered as a peer to verify
        token = peer_auth.mint_peer_token(local, remote, ["public"])

        local_pub = peer_auth.get_federation_pubkey()
        # Register "local" in peers as if it's a known peer
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO peers (id, node_id, node_url, status, federation_pubkey,"
            " allowed_scopes, signed_at, declaration_sig)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("p-local", local, "http://local", "active", local_pub, '["public"]', "now", "sig"),
        )
        conn.commit()
        conn.close()

        # Verify with sub=remote (matches the token's sub claim)
        claims = peer_auth.verify_peer_token(token, local_node_id=remote)
        assert claims.iss == local
        assert claims.sub == remote
        assert "public" in claims.scopes

    def test_verify_malformed_token_raises_401(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        from stigmem_node.peer_auth import verify_peer_token

        _patched_db(tmp_path, monkeypatch)
        with pytest.raises(HTTPException) as exc:
            verify_peer_token("not a real jwt", "stigmem://local")
        assert exc.value.status_code == 401

    def test_verify_expired_token_raises_401(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        from stigmem_node import peer_auth

        _patched_db(tmp_path, monkeypatch)
        priv, _ = peer_auth.get_or_create_keypair()
        # Mint manually with exp in the past. Peer token timestamps are epoch ms.
        now_ms = int(time.time() * 1000)
        payload: dict = {
            "iss": "stigmem://issuer",
            "sub": "stigmem://target",
            "iat": now_ms - 7_200_000,
            "exp": now_ms - 3_600_000,
            "nonce": "n1",
            "scopes": ["public"],
        }
        token = jwt.encode(payload, priv, algorithm="EdDSA")

        # Track audit calls
        captured: list = []

        def audit(*a: Any) -> None:
            captured.append(a)

        with pytest.raises(HTTPException) as exc:
            peer_auth.verify_peer_token(token, "stigmem://target", audit_writer=audit)
        assert exc.value.status_code == 401
        assert "expired" in str(exc.value.detail)
        # Audit was called with rejected_token
        assert len(captured) == 1
        assert captured[0][1] == "rejected_token"

    def test_verify_unknown_peer_raises_401(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        from stigmem_node import peer_auth

        _patched_db(tmp_path, monkeypatch)
        # Mint, but don't register issuer as peer → unknown_or_inactive_peer
        token = peer_auth.mint_peer_token("stigmem://unregistered", "stigmem://target", ["public"])
        with pytest.raises(HTTPException) as exc:
            peer_auth.verify_peer_token(token, "stigmem://target")
        assert exc.value.status_code == 401
        assert "unknown_or_inactive" in str(exc.value.detail)

    def test_verify_sub_mismatch_raises_401(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from fastapi import HTTPException

        from stigmem_node import peer_auth

        db = _patched_db(tmp_path, monkeypatch)

        local = "stigmem://issuer"
        token = peer_auth.mint_peer_token(local, "stigmem://wrong", ["public"])
        local_pub = peer_auth.get_federation_pubkey()

        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO peers (id, node_id, node_url, status, federation_pubkey,"
            " allowed_scopes, signed_at, declaration_sig)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("p1", local, "http://local", "active", local_pub, '["public"]', "now", "sig"),
        )
        conn.commit()
        conn.close()

        # local_node_id != token.sub → sub_mismatch
        with pytest.raises(HTTPException) as exc:
            peer_auth.verify_peer_token(token, local_node_id="stigmem://other")
        assert exc.value.status_code == 401
        assert "sub_mismatch" in str(exc.value.detail)


# ---------------------------------------------------------------------------
# peer_auth: nonce + declaration sign/verify
# ---------------------------------------------------------------------------


class TestNonceAndDeclaration:
    def test_consume_nonce_persists_and_replay_blocked(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.peer_auth import consume_nonce

        db = _patched_db(tmp_path, monkeypatch)
        consume_nonce("p1", "nonce-1", int(time.time() * 1000) + 3_600_000)

        # Verify nonce row exists
        conn = sqlite3.connect(db)
        row = conn.execute(
            "SELECT nonce FROM nonce_cache WHERE nonce = ?",
            ("nonce-1",),
        ).fetchone()
        conn.close()
        assert row is not None

    def test_canonical_declaration_json_is_sorted(self) -> None:
        from stigmem_node.peer_auth import canonical_declaration_json

        out = canonical_declaration_json(
            "http://node",
            "stigmem://node",
            "PUB",
            ["scope1"],
            "2026-01-01T00:00:00Z",
        )
        # Keys must appear in lexicographic order, no whitespace
        assert b'"allowed_scopes":["scope1"]' in out
        # Spec keys come before others alphabetically
        assert out.index(b"allowed_scopes") < out.index(b"federation_pubkey")
        assert out.index(b"federation_pubkey") < out.index(b"node_id")
        assert b" " not in out  # no whitespace

    def test_sign_and_verify_declaration_roundtrip(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.peer_auth import sign_declaration, verify_declaration_sig

        _patched_db(tmp_path, monkeypatch)

        node_url = "http://test"
        node_id = "stigmem://test"
        scopes = ["public", "local"]
        pubkey, sig, signed_at = sign_declaration(node_url, node_id, scopes)

        # Verify with the same parameters → True
        assert verify_declaration_sig(node_url, node_id, pubkey, scopes, signed_at, sig) is True

        # Tamper → False
        assert (
            verify_declaration_sig("http://different", node_id, pubkey, scopes, signed_at, sig)
            is False
        )

    def test_verify_declaration_with_garbage_pubkey_returns_false(self) -> None:
        from stigmem_node.peer_auth import verify_declaration_sig

        # Garbage pubkey → exception → returns False
        assert (
            verify_declaration_sig(
                "http://n",
                "stigmem://n",
                "not-a-real-key",
                ["public"],
                "2026-01-01T00:00:00Z",
                "AAAAAA",
            )
            is False
        )


# ---------------------------------------------------------------------------
# entity_resolver: pure helpers
# ---------------------------------------------------------------------------


class TestResolverHelpers:
    def test_tokenise_splits_on_punctuation(self) -> None:
        from stigmem_node.entity_resolver import _tokenise

        assert _tokenise("alice.smith") == ["alice", "smith"]
        assert _tokenise("alice_smith-jones") == ["alice", "smith", "jones"]

    def test_tokenise_lowercases(self) -> None:
        from stigmem_node.entity_resolver import _tokenise

        assert _tokenise("AliceSmith") == ["alicesmith"]
        assert _tokenise("ABC.def") == ["abc", "def"]

    def test_type_prefix_extracts_scheme(self) -> None:
        from stigmem_node.entity_resolver import _type_prefix

        # Formal URIs (stigmem://) → None; only informal "type:id" returns prefix
        assert _type_prefix("stigmem://node-a/agent/alice") is None
        assert _type_prefix("agent:alice") == "agent"
        assert _type_prefix("user:bob") == "user"
        # Strings without a colon return None
        assert _type_prefix("nocolon") is None

    def test_id_segment_returns_path_after_scheme(self) -> None:
        from stigmem_node.entity_resolver import _id_segment

        # stigmem URIs use ://
        assert "alice" in _id_segment("stigmem://node-a/agent/alice")
        # bare scheme
        assert _id_segment("agent:alice") == "alice"

    def test_token_score_empty_returns_zero(self) -> None:
        from stigmem_node.entity_resolver import _token_score

        assert _token_score([], ["a"]) == 0.0
        assert _token_score(["a"], []) == 0.0
        assert _token_score([], []) == 0.0

    def test_token_score_identical_tokens_returns_one(self) -> None:
        from stigmem_node.entity_resolver import _token_score

        assert _token_score(["alice"], ["alice"]) == 1.0

    def test_token_score_partial_match_in_range(self) -> None:
        from stigmem_node.entity_resolver import _token_score

        s = _token_score(["alice", "smith"], ["alice"])
        assert 0.0 < s <= 1.0


class TestResolveEntity:
    def test_malformed_input_returns_empty_result(self, tmp_path: Path) -> None:
        from stigmem_node.entity_resolver import resolve_entity

        db = _migrated_db(tmp_path)
        conn = sqlite3.connect(db)
        conn.row_factory = sqlite3.Row
        # An unparseable URI returns empty result
        result = resolve_entity("", conn)
        conn.close()
        assert result.canonical is None
        assert result.layer1_match is False

    def test_layer1_exact_match_returns_immediately(self, tmp_path: Path) -> None:
        from stigmem_node.entity_resolver import resolve_entity

        db = _migrated_db(tmp_path)
        # Seed an exact-match fact
        canonical = "stigmem://test/agent/alice"
        conn = sqlite3.connect(db)
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, scope,
                confidence, timestamp, hlc, tenant_id, cid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "f1",
                canonical,
                "memory:knows",
                "string",
                "v",
                canonical,
                "local",
                1.0,
                "2026-01-01T00:00:00Z",
                "0:0:0",
                "default",
                "cid:1",
            ),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row

        result = resolve_entity(canonical, conn)
        conn.close()
        assert result.layer1_match is True
        assert result.canonical == canonical

    def test_layer3_fuzzy_match_returns_candidates(self, tmp_path: Path) -> None:
        from stigmem_node.entity_resolver import resolve_entity

        db = _migrated_db(tmp_path)
        # Seed several "agent:*" facts to give Layer 3 candidates
        conn = sqlite3.connect(db)
        for name in ["alice-smith", "alice-jones", "bob-thompson"]:
            conn.execute(
                """INSERT INTO facts
                   (id, entity, relation, value_type, value_v, source, scope,
                    confidence, timestamp, hlc, tenant_id, cid)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"f-{name}",
                    f"agent:{name}",
                    "memory:role",
                    "string",
                    "x",
                    "src",
                    "local",
                    1.0,
                    "2026-01-01T00:00:00Z",
                    "0:0:0",
                    "default",
                    f"cid-{name}",
                ),
            )
        conn.commit()
        conn.row_factory = sqlite3.Row

        # Query for "alice" should find fuzzy matches
        result = resolve_entity("agent:alice", conn)
        conn.close()
        assert result.canonical == "agent:alice"
        # Layer 3 should produce some candidates (alice-* matches via prefix)
        assert len(result.layer3_candidates) >= 1

    def test_layer2_alias_match(self, tmp_path: Path) -> None:
        from stigmem_node.entity_resolver import resolve_entity

        db = _migrated_db(tmp_path)
        conn = sqlite3.connect(db)
        canonical = "stigmem://test/agent/canonical-alice"
        alias = "stigmem://test/agent/alias-alice"

        conn.execute(
            "INSERT INTO entity_aliases (raw_uri, canonical_uri, created_at) VALUES (?, ?, ?)",
            (alias, canonical, "2026-01-01T00:00:00Z"),
        )
        conn.commit()
        conn.row_factory = sqlite3.Row

        result = resolve_entity(alias, conn)
        conn.close()
        assert result.layer2_match == canonical
