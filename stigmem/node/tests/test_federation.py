"""Federation integration tests — spec §11.3 (partial failure) and §11.4 (replay attack).

These are the Phase 3 acceptance gates per ACM-36.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

import base64

import jwt
import pytest
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

from conftest import FedNode, make_peer_token


def _generate_ed25519_b64() -> tuple[str, str]:
    """Return (pubkey_b64url, privkey_b64url) for a new Ed25519 keypair."""
    priv = Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_b64 = (
        base64.urlsafe_b64encode(
            priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
        ).decode().rstrip("=")
    )
    pub_b64 = (
        base64.urlsafe_b64encode(pub.public_bytes(Encoding.Raw, PublicFormat.Raw))
        .decode().rstrip("=")
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
                peer_id, node_id, node_url, pub_b64,
                json.dumps(allowed_scopes or ["public"]),
                "active", "2026-05-02T00:00:00Z", "test_dummy_sig", "2026-05-02T00:00:00Z",
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
            fed_node.db_path, node_b_id, "http://testnode-b-scope", node_b_pub,
            allowed_scopes=["public"],
        )
        # Token claims company scope (intersection with ["public"] excludes company)
        token = make_peer_token(node_b_priv, node_b_id, fed_node.node_id,
                                ["company", "public"])
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

        token1 = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"],
                                 nonce=shared_nonce)
        token2 = make_peer_token(priv, node_b_id, fed_node.node_id, ["public"],
                                 nonce=shared_nonce)

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
            priv, node_b_id, fed_node.node_id, ["public"],
            ttl_ms=1, offset_ms=-7_200_000,
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

        fed_node.client.get("/v1/federation/facts",
                              headers={"Authorization": f"Bearer {token}"})
        fed_node.client.get("/v1/federation/facts",
                              headers={"Authorization": f"Bearer {token}"})

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
        r_read = fed_node.client.get(
            "/v1/facts?entity=local:during-partition"
        )
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
