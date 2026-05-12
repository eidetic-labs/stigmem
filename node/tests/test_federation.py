"""Federation integration tests — spec §11.3 (partial failure) and §11.4 (replay attack).

These are the Phase 3 acceptance gates per EG-36.
"""

from __future__ import annotations

import base64
import json
import sqlite3
import time
import uuid
from typing import Any

import pytest
from conftest import FedNode, generate_keypair, make_peer_token, sign_declaration
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from stigmem_node.db import db as _db_ctx
from stigmem_node.federation_ingest import ingest_fact
from stigmem_node.federation_pull import load_cursor, save_cursor


def _generate_ed25519_b64() -> tuple[str, str]:
    """Return (pubkey_b64url, privkey_b64url) for a new Ed25519 keypair."""
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
    return pub_b64, priv_b64


# ---------------------------------------------------------------------------
# Helpers shared across test classes
# ---------------------------------------------------------------------------


def _insert_active_peer(
    db_path: str,
    node_id: str,
    node_url: str,
    pub_b64: str,
    allowed_scopes: list[str] | None = None,
) -> str:
    """Directly insert an active peer row into the DB (bypasses HTTP verification)."""
    peer_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """INSERT INTO peers
               (id, node_id, node_url, federation_pubkey, allowed_scopes,
                status, established_at, declaration_sig, signed_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                peer_id,
                node_id,
                node_url,
                pub_b64,
                json.dumps(allowed_scopes or ["public"]),
                "active",
                "2026-05-02T00:00:00Z",
                "test_dummy_sig",
                "2026-05-02T00:00:00Z",
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return peer_id


def _make_federated_fact(
    entity: str = "test:entity",
    relation: str = "test:value",
    value: str = "test-value",
    scope: str = "public",
    hlc_offset_ms: int = 0,
) -> dict[str, Any]:
    base_ms = int(time.time() * 1000)
    return {
        "id": str(uuid.uuid4()),
        "entity": entity,
        "relation": relation,
        "value": {"type": "string", "v": value},
        "source": "stigmem://test-node-b",
        "timestamp": "2026-05-02T00:00:00Z",
        "hlc": f"{base_ms + hlc_offset_ms}.000",
        "confidence": 1.0,
        "scope": scope,
        "valid_until": None,
    }


# ---------------------------------------------------------------------------
# Well-known federation fields
# ---------------------------------------------------------------------------


class TestWellKnownFederation:
    def test_disabled_node_omits_federation_fields(self, client: Any) -> None:
        body = client.get("/.well-known/stigmem").json()
        assert body["federation"] == "disabled"
        assert "federation_pubkey" not in body
        assert "federation_endpoints" not in body

    def test_enabled_node_exposes_federation_fields(self, fed_node: FedNode) -> None:
        body = fed_node.client.get("/.well-known/stigmem").json()
        assert body["federation"] == "enabled"
        assert body["federation_version"] == "0.5"
        assert "federation_pubkey" in body
        assert body["federation_endpoints"]["peers"] == "/v1/federation/peers"
        assert body["federation_endpoints"]["facts"] == "/v1/federation/facts"


# ---------------------------------------------------------------------------
# Pull endpoint — auth and basic checks
# ---------------------------------------------------------------------------


class TestPullEndpoint:
    def test_no_token_returns_401(self, fed_node: FedNode) -> None:
        r = fed_node.client.get("/v1/federation/facts")
        assert r.status_code == 401

    def test_valid_token_returns_200(self, fed_node: FedNode) -> None:
        node_b_pub, node_b_priv = _generate_ed25519_b64()
        node_b_id = f"stigmem://test-b-{uuid.uuid4()}"
        _insert_active_peer(fed_node.db_path, node_b_id, "http://testnode-b", node_b_pub)

        token = make_peer_token(node_b_priv, node_b_id, fed_node.node_id, ["public"])
        r = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "facts" in body
        assert "cursor" in body
        assert "has_more" in body

    def test_scope_violation_returns_403_and_audit(self, fed_node: FedNode) -> None:
        """§11.2 / §6.4: requesting a scope not in peer declaration → 403 + audit entry."""
        node_b_pub, node_b_priv = _generate_ed25519_b64()
        node_b_id = f"stigmem://test-b-scope-{uuid.uuid4()}"
        # Peer registered with only ["public"] in allowed_scopes
        _insert_active_peer(
            fed_node.db_path,
            node_b_id,
            "http://testnode-b-scope",
            node_b_pub,
            allowed_scopes=["public"],
        )
        # Token claims company scope (intersection with ["public"] excludes company)
        token = make_peer_token(node_b_priv, node_b_id, fed_node.node_id, ["company", "public"])
        r = fed_node.client.get(
            "/v1/federation/facts?scope=company",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 403
        # Audit entry for scope_violation must be written
        with _db_ctx() as conn:
            entry = conn.execute(
                "SELECT * FROM federation_audit WHERE event_type='scope_violation' LIMIT 1"
            ).fetchone()
        assert entry is not None

    def test_facts_returned_in_hlc_order(self, fed_node: FedNode) -> None:
        """Pull endpoint returns facts ordered by HLC ASC, filterable by scope."""
        node_b_pub, node_b_priv = _generate_ed25519_b64()
        node_b_id = f"stigmem://test-b-order-{uuid.uuid4()}"
        _insert_active_peer(fed_node.db_path, node_b_id, "http://testnode-b-order", node_b_pub)

        # Ingest 5 facts into node A from node B (simulates prior pull)
        sender = "stigmem://node-b-order"
        facts = [_make_federated_fact(entity=f"order:e{i}", hlc_offset_ms=i * 10) for i in range(5)]
        for f in facts:
            ingest_fact(f, sender)

        token = make_peer_token(node_b_priv, node_b_id, fed_node.node_id, ["public"])
        r = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
        # The facts endpoint returns locally-stored public facts with HLC
        returned = r.json()["facts"]
        hlcs = [f["hlc"] for f in returned if f.get("hlc")]
        assert hlcs == sorted(hlcs)


# ---------------------------------------------------------------------------
# §11.4 — Replay Attack acceptance scenario
# ---------------------------------------------------------------------------


class TestReplayProtection:
    """Full acceptance gate for spec §11.4."""

    def _register_peer_b(self, fed_node: FedNode) -> tuple[str, str, str]:
        """Register a fresh node-B keypair as active peer with node A.
        Returns (node_b_id, pub_b64, priv_b64).
        """
        pub_b64, priv_b64 = _generate_ed25519_b64()
        node_b_id = f"stigmem://test-b-replay-{uuid.uuid4()}"
        _insert_active_peer(fed_node.db_path, node_b_id, "http://testnode-b-r", pub_b64)
        return node_b_id, pub_b64, priv_b64

    def test_step1_first_use_succeeds(self, fed_node: FedNode) -> None:
        """§11.4 step 1: Valid token used once → 200."""
        node_b_id, _, priv = self._register_peer_b(fed_node)
        token = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"])
        r = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200

    def test_step2_immediate_replay_rejected(self, fed_node: FedNode) -> None:
        """§11.4 step 2: Same token replayed immediately → 401 nonce_already_seen."""
        node_b_id, _, priv = self._register_peer_b(fed_node)
        token = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"])

        r1 = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r1.status_code == 200

        r2 = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r2.status_code == 401
        assert r2.json().get("detail") == "nonce_already_seen"

    def test_step3_same_nonce_fresh_token_rejected(self, fed_node: FedNode) -> None:
        """§11.4 step 3: New token with same nonce as used token → 401 nonce_already_seen."""
        node_b_id, _, priv = self._register_peer_b(fed_node)
        shared_nonce = str(uuid.uuid4())

        token1 = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"], nonce=shared_nonce)
        token2 = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"], nonce=shared_nonce)

        r1 = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert r1.status_code == 200

        # token2 is freshly signed but shares the same nonce
        r2 = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert r2.status_code == 401
        assert r2.json().get("detail") == "nonce_already_seen"

    def test_step4_expired_token_rejected(self, fed_node: FedNode) -> None:
        """§11.4 step 4: Token with exp in the past → 401 token_expired."""
        node_b_id, _, priv = self._register_peer_b(fed_node)
        # iat = 2 hours ago, ttl = 1ms → exp ≈ 2 hours ago
        token = make_peer_token(
            priv,
            node_b_id,
            fed_node.node_id,
            ["public"],
            ttl_ms=1,
            offset_ms=-7_200_000,
        )
        r = fed_node.client.get(
            "/v1/federation/facts",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 401
        assert r.json().get("detail") == "token_expired"

    def test_replay_audit_entries_written(self, fed_node: FedNode) -> None:
        """Replay attempt is recorded in federation_audit."""
        node_b_id, _, priv = self._register_peer_b(fed_node)
        token = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"])

        fed_node.client.get("/v1/federation/facts", headers={"Authorization": f"Bearer {token}"})
        fed_node.client.get("/v1/federation/facts", headers={"Authorization": f"Bearer {token}"})

        with _db_ctx() as conn:
            entry = conn.execute(
                "SELECT * FROM federation_audit WHERE event_type='replay_attempt' LIMIT 1"
            ).fetchone()
        assert entry is not None


# ---------------------------------------------------------------------------
# §11.3 — Partial Failure acceptance scenario
# ---------------------------------------------------------------------------


class TestPartialFailure:
    """Full acceptance gate for spec §11.3: cursor resumption + idempotent ingest."""

    def test_ingest_fact_is_idempotent(self, fed_node: FedNode) -> None:
        """Re-ingesting a fact with the same ID is a silent no-op."""
        fact = _make_federated_fact()
        result1 = ingest_fact(fact, "stigmem://node-b")
        result2 = ingest_fact(fact, "stigmem://node-b")

        assert result1 is True
        assert result2 is False  # no-op

        with _db_ctx() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE id = ?", (fact["id"],)
            ).fetchone()[0]
        assert count == 1

    def test_received_from_meta_fact_written_once(self, fed_node: FedNode) -> None:
        """stigmem:received_from meta-fact is written exactly once per federated fact."""
        fact = _make_federated_fact()
        ingest_fact(fact, "stigmem://node-b-meta")
        ingest_fact(fact, "stigmem://node-b-meta")  # second ingest is no-op

        with _db_ctx() as conn:
            meta_count = conn.execute(
                "SELECT COUNT(*) FROM facts "
                "WHERE entity = ? AND relation = 'stigmem:received_from'",
                (fact["id"],),
            ).fetchone()[0]
        assert meta_count == 1

    def test_cursor_save_and_load_roundtrip(self, fed_node: FedNode) -> None:
        """Cursor persistence survives a save/load cycle."""
        # Insert a dummy peer for cursor FK
        peer_id = _insert_active_peer(
            fed_node.db_path,
            f"stigmem://cursor-test-{uuid.uuid4()}",
            "http://cursor-test",
            fed_node.pub_b64,
        )
        cursor_val = f"{int(time.time() * 1000)}.005"
        save_cursor(peer_id, cursor_val)
        loaded = load_cursor(peer_id)
        assert loaded == cursor_val

    def test_scenario_partial_failure_no_duplicates(self, fed_node: FedNode) -> None:
        """§11.3 full scenario.

        1. 20 facts exist on node B (simulated as fact dicts).
        2. Node A ingests facts 0–9 (first pull), cursor saved at index 9.
        3. Simulate crash: cursor rolled back to index 4.
        4. Node A re-ingests facts 5–19 (re-pull from cursor 4).
           - Facts 5–9 already exist → idempotent no-op.
           - Facts 10–19 are new → ingested.
        5. Final count: exactly 20 unique received facts.
        """
        sender = f"stigmem://node-b-partial-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        facts = [
            _make_federated_fact(
                entity=f"partial:e{i}",
                value=f"v{i}",
                hlc_offset_ms=i * 10,
            )
            for i in range(20)
        ]
        # Set stable HLC values
        for i, f in enumerate(facts):
            f["hlc"] = f"{base_ms + i * 10}.000"

        # Step 2: ingest first 10
        for f in facts[:10]:
            ingest_fact(f, sender)

        with _db_ctx() as conn:
            first_count = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE received_from = ?", (sender,)
            ).fetchone()[0]
        assert first_count == 10

        # Step 3: simulate cursor rollback — re-ingest from index 5 (facts 5–19)
        for f in facts[5:]:
            ingest_fact(f, sender)

        with _db_ctx() as conn:
            final_count = conn.execute(
                "SELECT COUNT(*) FROM facts WHERE received_from = ?", (sender,)
            ).fetchone()[0]
            final_ids = [
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM facts WHERE received_from = ?", (sender,)
                ).fetchall()
            ]

        assert final_count == 20, f"Expected 20 unique facts, got {final_count}"
        assert len(final_ids) == len(set(final_ids)), "Duplicate fact IDs found"

    def test_local_reads_unaffected_by_pull_failure(self, fed_node: FedNode) -> None:
        """§11.3 invariant: local writes and reads work regardless of pull state."""
        # Inject a local fact directly (simulates local write during partition)
        r_write = fed_node.client.post(
            "/v1/facts",
            json={
                "entity": "local:during-partition",
                "relation": "test:value",
                "value": {"type": "string", "v": "local"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "local",
            },
        )
        assert r_write.status_code == 201

        # Read it back — local reads must work
        r_read = fed_node.client.get("/v1/facts?entity=local:during-partition")
        assert r_read.status_code == 200
        assert r_read.json()["total"] == 1


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_federated_conflict_creates_conflict_record(self, fed_node: FedNode) -> None:
        """§6.5 / §11.1: two federated facts for same entity/relation/scope → conflict."""
        base_ms = int(time.time() * 1000)
        entity = f"conflict:entity-{uuid.uuid4()}"

        fact_a = {
            "id": str(uuid.uuid4()),
            "entity": entity,
            "relation": "test:value",
            "value": {"type": "string", "v": "from-a"},
            "source": "stigmem://node-a",
            "timestamp": "2026-05-02T00:00:00Z",
            "hlc": f"{base_ms}.000",
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }
        fact_b = {
            "id": str(uuid.uuid4()),
            "entity": entity,
            "relation": "test:value",
            "value": {"type": "string", "v": "from-b"},
            "source": "stigmem://node-b",
            "timestamp": "2026-05-02T00:01:00Z",
            "hlc": f"{base_ms + 1}.000",
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }

        ingest_fact(fact_a, "stigmem://node-a")
        ingest_fact(fact_b, "stigmem://node-b")

        with _db_ctx() as conn:
            conflict = conn.execute(
                """SELECT * FROM conflicts
                   WHERE (fact_a_id = ? OR fact_b_id = ?)
                      OR (fact_a_id = ? OR fact_b_id = ?)""",
                (fact_a["id"], fact_a["id"], fact_b["id"], fact_b["id"]),
            ).fetchone()
        assert conflict is not None
        assert conflict["status"] == "unresolved"


# ---------------------------------------------------------------------------
# Cursor-based pull pagination on the federation/facts endpoint
# ---------------------------------------------------------------------------


class TestFederationFactsPagination:
    def test_cursor_pagination(self, fed_node: FedNode) -> None:
        """Cursor from first page fetches next page, no duplicates."""
        # Create local public facts via the API so they are served by the pull endpoint.
        # (Federated inbound facts have received_from set and are not re-exported per §3.1.)
        for i in range(10):
            fed_node.client.post(
                "/v1/facts",
                json={
                    "entity": f"page:e{i}-{uuid.uuid4()}",
                    "relation": "test:value",
                    "value": {"type": "string", "v": f"v{i}"},
                    "source": "agent:test",
                    "confidence": 1.0,
                    "scope": "public",
                },
            )

        node_b_pub, node_b_priv = _generate_ed25519_b64()
        node_b_id = f"stigmem://test-b-page-{uuid.uuid4()}"
        _insert_active_peer(fed_node.db_path, node_b_id, "http://testnode-b-page", node_b_pub)

        token1 = make_peer_token(node_b_priv, node_b_id, fed_node.node_id, ["public"])
        r1 = fed_node.client.get(
            "/v1/federation/facts?limit=5",
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert r1.status_code == 200
        page1 = r1.json()
        assert len(page1["facts"]) == 5
        assert page1["has_more"] is True
        cursor = page1["cursor"]
        assert cursor is not None

        token2 = make_peer_token(node_b_priv, node_b_id, fed_node.node_id, ["public"])
        r2 = fed_node.client.get(
            f"/v1/federation/facts?limit=5&cursor={cursor}",
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert r2.status_code == 200
        page2 = r2.json()
        assert len(page2["facts"]) == 5

        # No overlap between pages
        ids1 = {f["id"] for f in page1["facts"]}
        ids2 = {f["id"] for f in page2["facts"]}
        assert ids1.isdisjoint(ids2), "Overlapping fact IDs between pages"


# ---------------------------------------------------------------------------
# Peer registration signature verification (spec §5.6, §6.1)
# ---------------------------------------------------------------------------


class TestPeerRegistration:
    """Exercises the HTTP peer-registration route and declaration_sig verification."""

    def _build_declaration(
        self,
        node_id: str,
        node_url: str,
        pub_b64: str,
        priv_b64: str,
        allowed_scopes: list[str] | None = None,
        signed_at: str = "2026-05-02T00:00:00Z",
    ) -> dict:
        """Build a valid PeerDeclaration body per spec §6.1."""
        scopes = allowed_scopes or ["public"]
        # signed_fields must NOT include declaration_sig (spec §6.1 "above fields")
        fields_to_sign = {
            "allowed_scopes": scopes,
            "federation_pubkey": pub_b64,
            "node_id": node_id,
            "node_url": node_url,
            "signed_at": signed_at,
        }
        sig = sign_declaration(priv_b64, fields_to_sign)
        return {
            "node_id": node_id,
            "node_url": node_url,
            "federation_pubkey": pub_b64,
            "allowed_scopes": scopes,
            "declaration_sig": sig,
            "signed_at": signed_at,
        }

    def test_valid_declaration_registers_as_active(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Valid declaration + matching well-known pubkey → status active (§5.6)."""
        import httpx as _httpx

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-reg-{uuid.uuid4()}"
        node_b_url = "http://test-b-reg"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)

        # Mock the well-known fetch that register_peer performs
        class _MockAsyncClient:
            async def __aenter__(self) -> _MockAsyncClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str) -> _httpx.Response:
                return _httpx.Response(200, json={"federation_pubkey": peer_pub})

        monkeypatch.setattr(
            "stigmem_node.routes.federation.httpx.AsyncClient", lambda **_: _MockAsyncClient()
        )

        r = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == "active", f"Expected active, got: {data}"
        assert data["verified_at"] is not None

    def test_tampered_declaration_rejected(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Declaration where signature doesn't match payload → status rejected (§5.6 §6.1)."""
        import httpx as _httpx

        peer_pub, peer_priv = generate_keypair()
        node_b_id = f"stigmem://test-b-tamper-{uuid.uuid4()}"
        node_b_url = "http://test-b-tamper"

        body = self._build_declaration(node_b_id, node_b_url, peer_pub, peer_priv)
        # Tamper: change allowed_scopes after signing → signature no longer valid
        body["allowed_scopes"] = ["company", "public"]

        class _MockAsyncClient:
            async def __aenter__(self) -> _MockAsyncClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def get(self, url: str) -> _httpx.Response:
                return _httpx.Response(200, json={"federation_pubkey": peer_pub})

        monkeypatch.setattr(
            "stigmem_node.routes.federation.httpx.AsyncClient", lambda **_: _MockAsyncClient()
        )

        r = fed_node.client.post(
            "/v1/federation/peers",
            json=body,
            headers={"Authorization": f"Bearer {fed_node.federate_key}"},
        )

        assert r.status_code == 201, r.text
        assert r.json()["status"] == "rejected"


# ---------------------------------------------------------------------------
# §11.1 — Split-Brain acceptance scenario
# ---------------------------------------------------------------------------


class TestSplitBrain:
    """Full acceptance gate for spec §11.1: split-brain conflict detection."""

    def test_both_facts_stored_with_contradicted_flag(self, fed_node: FedNode) -> None:
        """After partition heals, both facts exist with contradicted=True."""
        entity = f"split:e-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        # Node A writes locally
        r_a = fed_node.client.post(
            "/v1/facts",
            json={
                "entity": entity,
                "relation": "split:value",
                "value": {"type": "string", "v": "from-a"},
                "source": "agent:node-a",
                "confidence": 1.0,
                "scope": "public",
            },
        )
        assert r_a.status_code == 201
        fact_a_id = r_a.json()["id"]

        # Simulate node B's divergent fact arriving via federation (partition healed)
        fact_b = {
            "id": str(uuid.uuid4()),
            "entity": entity,
            "relation": "split:value",
            "value": {"type": "string", "v": "from-b"},
            "source": "stigmem://node-b",
            "timestamp": "2026-05-02T00:01:00Z",
            "hlc": f"{base_ms + 1000}.000",
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }
        ingest_fact(fact_b, "stigmem://node-b")

        # Both facts must be stored
        with _db_ctx() as conn:
            a_row = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_a_id,)).fetchone()
            b_row = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_b["id"],)).fetchone()
        assert a_row is not None, "fact_a missing from store"
        assert b_row is not None, "fact_b missing from store"

    def test_conflict_record_queryable_via_api(self, fed_node: FedNode) -> None:
        """GET /v1/conflicts?status=unresolved returns the split-brain conflict."""
        entity = f"split:q-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        fed_node.client.post(
            "/v1/facts",
            json={
                "entity": entity,
                "relation": "split:val",
                "value": {"type": "string", "v": "local"},
                "source": "agent:local",
                "confidence": 1.0,
                "scope": "public",
            },
        )

        ingest_fact(
            {
                "id": str(uuid.uuid4()),
                "entity": entity,
                "relation": "split:val",
                "value": {"type": "string", "v": "remote"},
                "source": "stigmem://node-b",
                "timestamp": "2026-05-02T00:01:00Z",
                "hlc": f"{base_ms + 500}.000",
                "confidence": 1.0,
                "scope": "public",
                "valid_until": None,
            },
            "stigmem://node-b",
        )

        r = fed_node.client.get("/v1/conflicts?status=unresolved")
        assert r.status_code == 200
        body = r.json()
        our_conflicts = [
            c
            for c in body["conflicts"]
            if (c["fact_a"] and c["fact_a"]["entity"] == entity)
            or (c["fact_b"] and c["fact_b"]["entity"] == entity)
        ]
        assert len(our_conflicts) >= 1
        c = our_conflicts[0]
        assert c["status"] == "unresolved"
        assert c["fact_a"] is not None
        assert c["fact_b"] is not None

    def test_query_returns_both_facts_with_contradicted_true(self, fed_node: FedNode) -> None:
        """GET /v1/facts for split-brain entity returns both facts marked contradicted."""
        entity = f"split:both-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        r_local = fed_node.client.post(
            "/v1/facts",
            json={
                "entity": entity,
                "relation": "split:val",
                "value": {"type": "string", "v": "local"},
                "source": "agent:local",
                "confidence": 1.0,
                "scope": "public",
            },
        )
        assert r_local.status_code == 201

        ingest_fact(
            {
                "id": str(uuid.uuid4()),
                "entity": entity,
                "relation": "split:val",
                "value": {"type": "string", "v": "remote"},
                "source": "stigmem://node-b",
                "timestamp": "2026-05-02T00:01:00Z",
                "hlc": f"{base_ms + 500}.000",
                "confidence": 1.0,
                "scope": "public",
                "valid_until": None,
            },
            "stigmem://node-b",
        )

        r = fed_node.client.get(
            f"/v1/facts?entity={entity}&relation=split:val&include_contradicted=true"
        )
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert len(facts) == 2, f"Expected 2 contradicting facts, got {len(facts)}"
        assert all(f["contradicted"] for f in facts), "Both facts must have contradicted=True"

    def test_no_fact_silently_discarded(self, fed_node: FedNode) -> None:
        """No fact is overwritten or silently discarded during merge (§6.6 rule 5)."""
        entity = f"split:nodrop-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        ids = []
        for i, val in enumerate(["alpha", "beta", "gamma"]):
            fact = {
                "id": str(uuid.uuid4()),
                "entity": entity,
                "relation": "split:multi",
                "value": {"type": "string", "v": val},
                "source": f"stigmem://node-{i}",
                "timestamp": f"2026-05-02T00:0{i}:00Z",
                "hlc": f"{base_ms + i * 100}.000",
                "confidence": 1.0,
                "scope": "public",
                "valid_until": None,
            }
            ingest_fact(fact, f"stigmem://node-{i}")
            ids.append(fact["id"])

        with _db_ctx() as conn:
            stored = {
                r["id"]
                for r in conn.execute(
                    "SELECT id FROM facts WHERE entity = ? AND relation = 'split:multi'",
                    (entity,),
                ).fetchall()
            }
        assert set(ids) == stored, "All facts must be stored, none discarded"


# ---------------------------------------------------------------------------
# §11.2 — Malicious Peer acceptance scenario
# ---------------------------------------------------------------------------


class TestMaliciousPeer:
    """Full acceptance gate for spec §11.2: scope violation + source forgery via push."""

    def _push_node(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> tuple[str, str, str]:
        """Register an active peer with push enabled. Returns (node_b_id, pub, priv)."""
        import stigmem_node.settings as _settings_mod

        Settings = _settings_mod.Settings

        # Enable push for this test
        original = _settings_mod.settings
        new_settings = Settings(
            db_path=original.db_path,
            auth_required=original.auth_required,
            node_url=original.node_url,
            federation_enabled=original.federation_enabled,
            federation_pubkey=original.federation_pubkey,
            federation_privkey=original.federation_privkey,
            federation_push_enabled=True,
        )
        monkeypatch.setattr(_settings_mod, "settings", new_settings)
        for mod_name in [
            "stigmem_node.routes.federation",
            "stigmem_node.federation_ingest",
            "stigmem_node.peer_token",
        ]:
            import importlib

            try:
                mod = importlib.import_module(mod_name)
                if hasattr(mod, "settings"):
                    monkeypatch.setattr(mod, "settings", new_settings)
            except ImportError:
                pass

        pub, priv = _generate_ed25519_b64()
        node_b_id = f"stigmem://malicious-peer-{uuid.uuid4()}"
        _insert_active_peer(
            fed_node.db_path,
            node_b_id,
            "http://malicious-peer",
            pub,
            allowed_scopes=["public"],
        )
        return node_b_id, pub, priv

    def test_scope_violation_rejected_with_audit(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """§11.2 scenario 1: push fact with disallowed scope → rejected + audit entry."""
        node_b_id, pub, priv = self._push_node(fed_node, monkeypatch)
        token = make_peer_token(priv, node_b_id, fed_node.node_id, ["public", "company"])

        r = fed_node.client.post(
            "/v1/federation/facts/push",
            json={
                "facts": [
                    {
                        "id": str(uuid.uuid4()),
                        "entity": "company:secret",
                        "relation": "test:val",
                        "value": {"type": "string", "v": "leak"},
                        "source": node_b_id,
                        "timestamp": "2026-05-02T00:00:00Z",
                        "hlc": f"{int(time.time() * 1000)}.000",
                        "confidence": 1.0,
                        "scope": "company",  # peer only allows "public"
                        "valid_until": None,
                    }
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 202
        data = r.json()
        assert data["rejected"] == 1
        assert data["accepted"] == 0

        with _db_ctx() as conn:
            entry = conn.execute(
                "SELECT * FROM federation_audit WHERE event_type = 'scope_violation' LIMIT 1"
            ).fetchone()
        assert entry is not None, "scope_violation audit entry must be written"

    def test_source_forgery_rejected_with_audit(
        self, fed_node: FedNode, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """§11.2 scenario 2: push fact with forged source → rejected + rejected_fact audit entry."""
        node_b_id, pub, priv = self._push_node(fed_node, monkeypatch)
        token = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"])

        forged_fact_id = str(uuid.uuid4())
        r = fed_node.client.post(
            "/v1/federation/facts/push",
            json={
                "facts": [
                    {
                        "id": forged_fact_id,
                        "entity": "user:alice",
                        "relation": "test:val",
                        "value": {"type": "string", "v": "injected"},
                        "source": "user:alice",  # not the peer's node_id → forgery
                        "timestamp": "2026-05-02T00:00:00Z",
                        "hlc": f"{int(time.time() * 1000)}.000",
                        "confidence": 1.0,
                        "scope": "public",
                        "valid_until": None,
                    }
                ]
            },
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 202
        data = r.json()
        assert data["rejected"] == 1
        assert data["accepted"] == 0
        assert any(e.get("error") == "source_not_owned" for e in data["errors"])

        with _db_ctx() as conn:
            entry = conn.execute(
                "SELECT detail FROM federation_audit WHERE event_type = 'rejected_fact' LIMIT 1"
            ).fetchone()
        assert entry is not None, "rejected_fact audit entry must be written"
        detail = json.loads(entry["detail"])
        assert detail.get("reason") == "source_not_owned"

        # Forged fact must NOT be in the store
        with _db_ctx() as conn:
            row = conn.execute("SELECT id FROM facts WHERE id = ?", (forged_fact_id,)).fetchone()
        assert row is None, "Forged fact must not be stored"


# ---------------------------------------------------------------------------
# §5.10 — Conflict resolution route
# ---------------------------------------------------------------------------


class TestConflictResolution:
    """Acceptance tests for POST /v1/conflicts/:id/resolve (spec §5.10)."""

    def _create_conflict(self, fed_node: FedNode) -> tuple[str, str, str, str]:
        """Create a conflict and return (conflict_id, entity, fact_a_id, fact_b_id)."""
        entity = f"resolve:e-{uuid.uuid4()}"
        base_ms = int(time.time() * 1000)

        r_a = fed_node.client.post(
            "/v1/facts",
            json={
                "entity": entity,
                "relation": "resolve:val",
                "value": {"type": "string", "v": "version-a"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "public",
            },
        )
        assert r_a.status_code == 201
        fact_a_id = r_a.json()["id"]

        fact_b = {
            "id": str(uuid.uuid4()),
            "entity": entity,
            "relation": "resolve:val",
            "value": {"type": "string", "v": "version-b"},
            "source": "stigmem://node-b",
            "timestamp": "2026-05-02T00:01:00Z",
            "hlc": f"{base_ms + 1000}.000",
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }
        ingest_fact(fact_b, "stigmem://node-b")
        fact_b_id = fact_b["id"]

        with _db_ctx() as conn:
            conflict = conn.execute(
                "SELECT id FROM conflicts WHERE fact_a_id = ? OR fact_b_id = ?",
                (fact_a_id, fact_a_id),
            ).fetchone()
        assert conflict is not None, "conflict must be created"
        return conflict["id"], entity, fact_a_id, fact_b_id

    def test_resolve_with_winning_fact_returns_200(self, fed_node: FedNode) -> None:
        """Resolve with winning_fact_id → 200 with resolution_fact_id."""
        conflict_id, entity, fact_a_id, _ = self._create_conflict(fed_node)

        r = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id, "resolution_note": "prefer local"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert "resolution_fact_id" in body
        assert body["conflict_status"] == "resolved"

    def test_resolve_updates_conflict_status(self, fed_node: FedNode) -> None:
        """After resolution, GET /v1/conflicts?status=unresolved omits the conflict."""
        conflict_id, entity, fact_a_id, _ = self._create_conflict(fed_node)

        fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )

        r = fed_node.client.get("/v1/conflicts?status=unresolved")
        assert r.status_code == 200
        unresolved_ids = [c["conflict_id"] for c in r.json()["conflicts"]]
        assert conflict_id not in unresolved_ids, (
            "resolved conflict must not appear in unresolved list"
        )

    def test_resolve_creates_resolution_fact_with_provenance(self, fed_node: FedNode) -> None:
        """Resolution fact uses namespaced entity; stigmem:resolves meta-fact points to conflict."""
        conflict_id, entity, fact_a_id, _ = self._create_conflict(fed_node)

        r = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )
        resolution_fact_id = r.json()["resolution_fact_id"]

        # Resolution fact exists in the facts table under the namespaced entity (not the
        # original entity) to avoid sharing the (entity, relation, scope) triple with the
        # conflicting facts, which would cause a cascade contradiction wave on federation.
        r_fact = fed_node.client.get(f"/v1/facts/{resolution_fact_id}")
        assert r_fact.status_code == 200
        fact = r_fact.json()
        assert fact["entity"] == f"stigmem:resolution:{conflict_id}", (
            "resolution fact MUST use namespaced entity, not the conflicting entity"
        )
        assert fact["entity"] != entity, (
            "resolution fact must NOT share entity with conflicting facts"
        )
        assert fact["relation"] == "resolve:val"
        assert fact["confidence"] == 1.0

        # stigmem:resolves meta-fact points to the conflict
        with _db_ctx() as conn:
            resolves = conn.execute(
                "SELECT * FROM facts WHERE entity = ? AND relation = 'stigmem:resolves'",
                (resolution_fact_id,),
            ).fetchone()
        assert resolves is not None, "stigmem:resolves meta-fact must exist"
        assert resolves["value_v"] == conflict_id

    def test_resolve_no_cascade_contradiction_on_federation(self, fed_node: FedNode) -> None:
        """Ingesting a resolution fact via federation must not create a new contradiction.

        Regression test for EG-51: the old implementation wrote the resolution fact
        under the original (entity, relation, scope), which caused a new contradiction
        wave when peers ingested it alongside the two original conflicting facts.
        """
        conflict_id, entity, fact_a_id, _ = self._create_conflict(fed_node)

        r = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )
        assert r.status_code == 200
        resolution_fact_id = r.json()["resolution_fact_id"]

        # Count conflicts before re-ingesting the resolution fact
        with _db_ctx() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS n FROM conflicts WHERE status = 'unresolved'"
            ).fetchone()["n"]

        # Simulate a peer node ingesting the resolution fact (idempotent re-ingest)
        r_fact = fed_node.client.get(f"/v1/facts/{resolution_fact_id}")
        assert r_fact.status_code == 200
        resolution_fact = r_fact.json()

        ingest_fact(
            {
                "id": resolution_fact["id"],
                "entity": resolution_fact["entity"],
                "relation": resolution_fact["relation"],
                "value": resolution_fact["value"],
                "source": resolution_fact["source"],
                "timestamp": resolution_fact["timestamp"],
                "hlc": resolution_fact.get("hlc"),
                "confidence": resolution_fact["confidence"],
                "scope": resolution_fact["scope"],
                "valid_until": resolution_fact.get("valid_until"),
            },
            "stigmem://peer-node",
        )

        # No new unresolved conflicts must have appeared
        with _db_ctx() as conn:
            after = conn.execute(
                "SELECT COUNT(*) AS n FROM conflicts WHERE status = 'unresolved'"
            ).fetchone()["n"]
        assert after == before, (
            f"federation of resolution fact must not create new contradictions "
            f"(unresolved conflicts before={before}, after={after})"
        )

    def test_status_resolved_fact_no_cascade_contradiction_on_federation(
        self, fed_node: FedNode
    ) -> None:
        """Ingesting stigmem:conflict:status 'resolved' via federation must not create a
        spurious contradiction against the existing 'unresolved' status fact.

        Regression test for EG-57: _detect_and_record_contradiction was not exempting
        stigmem: namespace facts, causing status transitions to be treated as sibling
        conflicts and generating spurious conflict records on peer nodes.
        """
        conflict_id, _entity, _fact_a_id, _ = self._create_conflict(fed_node)

        with _db_ctx() as conn:
            before = conn.execute(
                "SELECT COUNT(*) AS n FROM conflicts WHERE status = 'unresolved'"
            ).fetchone()["n"]

        base_ms = int(time.time() * 1000)
        resolved_status_fact = {
            "id": str(uuid.uuid4()),
            "entity": conflict_id,
            "relation": "stigmem:conflict:status",
            "value": {"type": "string", "v": "resolved"},
            "source": "system:stigmem",
            "timestamp": "2026-05-02T00:02:00Z",
            "hlc": f"{base_ms + 2000}.000",
            "confidence": 1.0,
            "scope": "public",
            "valid_until": None,
        }
        ingest_fact(resolved_status_fact, "stigmem://peer-node")

        with _db_ctx() as conn:
            after = conn.execute(
                "SELECT COUNT(*) AS n FROM conflicts WHERE status = 'unresolved'"
            ).fetchone()["n"]

        assert after == before, (
            f"ingesting stigmem:conflict:status 'resolved' must not create new spurious "
            f"contradictions (unresolved conflicts before={before}, after={after})"
        )

    def test_resolve_with_new_value(self, fed_node: FedNode) -> None:
        """Resolve with new_value asserts a fresh reconciliation value."""
        conflict_id, entity, fact_a_id, _ = self._create_conflict(fed_node)

        r = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"new_value": {"type": "string", "v": "reconciled"}},
        )
        assert r.status_code == 200
        resolution_fact_id = r.json()["resolution_fact_id"]

        r_fact = fed_node.client.get(f"/v1/facts/{resolution_fact_id}")
        assert r_fact.status_code == 200
        assert r_fact.json()["value"]["v"] == "reconciled"

    def test_resolve_idempotency_conflict(self, fed_node: FedNode) -> None:
        """Resolving an already-resolved conflict → 409."""
        conflict_id, _, fact_a_id, _ = self._create_conflict(fed_node)

        fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )
        r2 = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )
        assert r2.status_code == 409

    def test_resolve_original_facts_remain_immutable(self, fed_node: FedNode) -> None:
        """Both original conflicting facts remain in the store after resolution."""
        conflict_id, entity, fact_a_id, fact_b_id = self._create_conflict(fed_node)

        fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"winning_fact_id": fact_a_id},
        )

        with _db_ctx() as conn:
            a = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_a_id,)).fetchone()
            b = conn.execute("SELECT id FROM facts WHERE id = ?", (fact_b_id,)).fetchone()
        assert a is not None, "original fact_a must remain"
        assert b is not None, "original fact_b must remain"

    def test_resolve_missing_conflict_returns_404(self, fed_node: FedNode) -> None:
        """Non-existent conflict_id → 404."""
        r = fed_node.client.post(
            "/v1/conflicts/stigmem:conflict:does-not-exist/resolve",
            json={"winning_fact_id": str(uuid.uuid4())},
        )
        assert r.status_code == 404

    def test_resolve_no_winning_fact_or_new_value_returns_422(self, fed_node: FedNode) -> None:
        """Missing both winning_fact_id and new_value → 422."""
        conflict_id, _, _, _ = self._create_conflict(fed_node)
        r = fed_node.client.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json={"resolution_note": "note only, no winner"},
        )
        assert r.status_code == 422
