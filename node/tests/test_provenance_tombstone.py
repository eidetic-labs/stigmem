"""Tests for §23.3.2 r.4 — tombstone suppression in provenance walk.

Coverage:
- derived_from entry pointing to a tombstoned entity → {exists: false}
- derived_from entry pointing to a live (non-tombstoned) fact → {exists: true, entity, fact_id}
- Mixed: only tombstoned entries suppressed; live entries pass through
- exists:false shape is identical to §20.6.2 unauthorized pattern (no leaking fields)
- Fact with no derived_from returns an empty list
- Provenance of a non-existent fact returns 404
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_fact(client: TestClient, entity: str, value: str = "test") -> dict:
    resp = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": "test:name",
            "value": {"type": "string", "v": value},
            "source": entity,
            "scope": "local",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _set_derived_from(db_path: str, fact_id: str, derived_from: list[dict]) -> None:
    """Directly update a fact row's derived_from JSON (no write API for this field yet)."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE facts SET derived_from = ? WHERE id = ?",
        (json.dumps(derived_from), fact_id),
    )
    conn.commit()
    conn.close()


def _insert_tombstone(db_path: str, entity_uri: str) -> str:
    tomb_id = f"tomb_{uuid.uuid4().hex}"
    now = datetime.now(UTC).isoformat()
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO tombstones
           (id, entity_uri, scope, reason, signed_by, signature, created_at, legal_hold, tenant_id)
           VALUES (?,?,?,?,?,?,?,0,'default')""",
        (tomb_id, entity_uri, "*", "rtbf-test", "agent:admin", "fake-sig", now),
    )
    conn.commit()
    conn.close()
    return tomb_id


# ---------------------------------------------------------------------------
# §23.3.2 r.4 — tombstone suppression in provenance walk
# ---------------------------------------------------------------------------


class TestProvenanceTombstoneSuppression:
    def test_tombstoned_entity_derived_from_returns_exists_false(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """Retract entity A; walk provenance of fact derived from A → exists:false."""
        entity_a = "stigmem://test/entity/alpha"
        entity_b = "stigmem://test/entity/beta"

        f1 = _insert_fact(client, entity=entity_a, value="alpha data")
        f2 = _insert_fact(client, entity=entity_b, value="derived from alpha")
        _set_derived_from(
            tmp_db,
            f2["id"],
            [{"hash": f1.get("cid") or f"sha256:{'0' * 64}", "fact_id": f1["id"]}],
        )

        _insert_tombstone(tmp_db, entity_a)

        resp = client.get(f"/v1/facts/{f2['id']}/provenance")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["fact_id"] == f2["id"]
        assert len(data["derived_from"]) == 1
        entry = data["derived_from"][0]
        assert entry["exists"] is False
        assert entry.get("entity") is None
        assert entry.get("fact_id") is None

    def test_non_tombstoned_entity_derived_from_returns_exists_true(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """Non-tombstoned derived_from entry is returned with full data."""
        entity_a = "stigmem://test/entity/gamma"
        entity_b = "stigmem://test/entity/delta"

        f1 = _insert_fact(client, entity=entity_a, value="gamma data")
        f2 = _insert_fact(client, entity=entity_b, value="derived from gamma")
        _set_derived_from(
            tmp_db,
            f2["id"],
            [{"hash": f1.get("cid") or f"sha256:{'0' * 64}", "fact_id": f1["id"]}],
        )

        # No tombstone on entity_a
        resp = client.get(f"/v1/facts/{f2['id']}/provenance")
        assert resp.status_code == 200, resp.text
        entry = resp.json()["derived_from"][0]
        assert entry["exists"] is True
        assert entry["entity"] == entity_a
        assert entry["fact_id"] == f1["id"]

    def test_mixed_entries_only_tombstoned_suppressed(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """Only the tombstoned entity's entry is redacted; the live entry passes through."""
        entity_tombed = "stigmem://test/entity/tombed"
        entity_alive = "stigmem://test/entity/alive"
        entity_derived = "stigmem://test/entity/derived"

        f_tomb = _insert_fact(client, entity=entity_tombed, value="to be forgotten")
        f_alive = _insert_fact(client, entity=entity_alive, value="staying alive")
        f_derived = _insert_fact(client, entity=entity_derived, value="derived from both")

        _set_derived_from(
            tmp_db,
            f_derived["id"],
            [
                {"hash": f_tomb.get("cid") or f"sha256:{'1' * 64}", "fact_id": f_tomb["id"]},
                {"hash": f_alive.get("cid") or f"sha256:{'2' * 64}", "fact_id": f_alive["id"]},
            ],
        )

        _insert_tombstone(tmp_db, entity_tombed)

        resp = client.get(f"/v1/facts/{f_derived['id']}/provenance")
        assert resp.status_code == 200, resp.text
        entries = resp.json()["derived_from"]
        assert len(entries) == 2

        # Order preserved: tombstoned entry first, live entry second
        assert entries[0]["exists"] is False
        assert entries[0].get("entity") is None
        assert entries[1]["exists"] is True
        assert entries[1]["entity"] == entity_alive

    def test_exists_false_shape_indistinguishable_from_unauthorized(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """§20.6.2 + §23.3.2 r.4: exists:false exposes only hash — no entity/fact_id leak."""
        entity_a = "stigmem://test/entity/secret"
        entity_b = "stigmem://test/entity/public"

        f1 = _insert_fact(client, entity=entity_a, value="secret data")
        f2 = _insert_fact(client, entity=entity_b, value="derived data")
        _set_derived_from(
            tmp_db,
            f2["id"],
            [{"hash": f1.get("cid") or f"sha256:{'a' * 64}", "fact_id": f1["id"]}],
        )
        _insert_tombstone(tmp_db, entity_a)

        resp = client.get(f"/v1/facts/{f2['id']}/provenance")
        assert resp.status_code == 200
        entry = resp.json()["derived_from"][0]

        assert entry["exists"] is False
        # No leaking fields — caller cannot tell tombstone from unauthorized
        assert entry.get("fact_id") is None
        assert entry.get("entity") is None

    def test_no_derived_from_returns_empty_list(
        self, client: TestClient, tmp_db: str
    ) -> None:
        """A fact without derived_from returns derived_from: []."""
        entity = "stigmem://test/entity/standalone"
        f = _insert_fact(client, entity=entity, value="no provenance")

        resp = client.get(f"/v1/facts/{f['id']}/provenance")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fact_id"] == f["id"]
        assert data["derived_from"] == []

    def test_provenance_of_nonexistent_fact_returns_404(self, client: TestClient) -> None:
        """Walking provenance of a non-existent fact returns 404."""
        resp = client.get(f"/v1/facts/{uuid.uuid4()}/provenance")
        assert resp.status_code == 404
