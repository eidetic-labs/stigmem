from __future__ import annotations

import logging
import time
import uuid

from conftest import FedNode

from stigmem_node.db import db as _db_ctx
from stigmem_node.federation_ingest import ingest_fact
from stigmem_node.federation_pull import load_cursor, save_cursor

from .helpers import insert_active_peer, make_federated_fact

logger = logging.getLogger(__name__)


class TestPartialFailure:
    """Full acceptance gate for spec §11.3: cursor resumption + idempotent ingest."""

    def test_ingest_fact_is_idempotent(self, fed_node: FedNode) -> None:
        """Re-ingesting a fact with the same ID is a silent no-op."""
        fact = make_federated_fact()
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
        fact = make_federated_fact()
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
        peer_id = insert_active_peer(
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
            make_federated_fact(
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
