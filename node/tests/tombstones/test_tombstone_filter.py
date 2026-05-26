"""Tombstone filter tests — spec §23.3.2 r.3 (recall) and §23.3.3 r.2 (subscription delivery).

Coverage:
- Subscription events for tombstoned entities are dropped (not delivered to webhook)
- Tombstoned events are marked 'delivered' so they are not retried
- Memory cards with a tombstoned about_entity are excluded from recall results
- Raw facts for tombstoned entities are excluded from recall results
- Active tombstone cache invalidation forces a DB re-read on next check
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic, sleep
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.subscription_delivery as delivery_mod
import stigmem_node.tombstone_cache as tc_mod
from stigmem_node.plugins.testing import stigmem_plugins

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_ENTITY = "stigmem://test/agent/alice"
_TENANT = "default"
_TOMBSTONE_PLUGIN_SRC = (
    Path(__file__).resolve().parents[3] / "experimental" / "tombstones" / "src"
)


def _tombstone_plugin_manifest():
    import sys

    if str(_TOMBSTONE_PLUGIN_SRC) not in sys.path:
        sys.path.insert(0, str(_TOMBSTONE_PLUGIN_SRC))
    plugin = __import__("stigmem_plugin_tombstones")
    return plugin.plugin_manifest()


@pytest.fixture(autouse=True)
def _tombstone_plugin_registered(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ENABLED", "true")
    monkeypatch.setenv("STIGMEM_TOMBSTONES_ALLOW_RECALL_FILTER", "true")
    with stigmem_plugins([_tombstone_plugin_manifest()]):
        yield


def _insert_tombstone(
    entity_uri: str,
    tenant_id: str = _TENANT,
    *,
    legal_hold: bool = False,
) -> str:
    """Insert an active (non-revoked) tombstone row; return its id."""
    tomb_id = f"tomb_{uuid.uuid4()}"
    now = datetime.now(UTC).isoformat()
    with db_mod.db() as conn:
        conn.execute(
            """INSERT INTO tombstones
               (id, entity_uri, scope, reason, signed_by, signature,
                created_at, legal_hold, tenant_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                tomb_id,
                entity_uri,
                "*",
                "test-rtbf",
                "test-admin",
                "sig-placeholder",
                now,
                1 if legal_hold else 0,
                tenant_id,
            ),
        )
    return tomb_id


def _revoke_tombstone(tombstone_id: str) -> None:
    rev_id = f"tombrevoke_{uuid.uuid4()}"
    now = datetime.now(UTC).isoformat()
    with db_mod.db() as conn:
        conn.execute(
            """INSERT INTO tombstone_revocations
               (id, tombstone_id, reason, signed_by, signature, created_at)
               VALUES (?,?,?,?,?,?)""",
            (rev_id, tombstone_id, "reinstated", "test-admin", "rev-sig", now),
        )


def _insert_fact(client: TestClient, entity: str = _ENTITY, value: str = "Alice") -> dict:
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


def _create_subscription(client: TestClient, target: str = "local") -> dict:
    subscriber = f"stigmem://test/agent/subscriber/{uuid.uuid4()}"
    raw_key = auth_mod.create_api_key(subscriber, ["read"])
    resp = client.post(
        "/v1/subscriptions",
        json={
            "target": target,
            "on_change": "webhook",
            "delivery_address": "https://example.com/hook",
        },
        headers={"Authorization": f"Bearer {raw_key}"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _drain_subscription_delivery(*, timeout_s: float = 2.0) -> None:
    """Run the best-effort delivery sweep until this test's events are drained.

    ``deliver_pending`` intentionally returns without work when another sweep
    holds the process-wide claim lock. The full suite can briefly overlap with
    background delivery tasks, so these tests wait for a settled DB state
    instead of relying on a single best-effort call.
    """
    deadline = monotonic() + timeout_s
    while True:
        while not delivery_mod._DELIVER_PENDING_LOCK.acquire(blocking=False):  # noqa: SLF001
            if monotonic() >= deadline:
                raise AssertionError("subscription delivery lock did not become idle")
            sleep(0.01)
        delivery_mod._DELIVER_PENDING_LOCK.release()  # noqa: SLF001
        delivery_mod.deliver_pending()
        with db_mod.db() as conn:
            row = conn.execute(
                """SELECT COUNT(*) AS n
                   FROM subscription_events
                   WHERE delivery_status IN ('pending', 'delivering')"""
            ).fetchone()
        if row["n"] == 0:
            return
        if monotonic() >= deadline:
            raise AssertionError(f"subscription delivery did not drain; remaining={row['n']}")
        sleep(0.01)


def _recall(client: TestClient, query: str = "alice") -> list[dict]:
    resp = client.post(
        "/v1/recall",
        json={"query": query, "scope": "local", "token_budget": 4000, "include_neighbors": False},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["facts"]


# ---------------------------------------------------------------------------
# §23.3.3 r.2 — subscription delivery suppression
# ---------------------------------------------------------------------------


class TestTombstoneSubscriptionDelivery:
    def test_event_not_delivered_to_webhook_after_tombstone(self, client: TestClient) -> None:
        """Tombstoned entity: webhook NOT called; event IS marked delivered."""
        sub = _create_subscription(client)
        _insert_fact(client)

        _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("stigmem_node.subscription_delivery.httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.__enter__ = MagicMock(return_value=mock_inst)
            mock_inst.__exit__ = MagicMock(return_value=False)
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value = mock_inst

            _drain_subscription_delivery()

            mock_inst.post.assert_not_called()

        # Event should be marked delivered (silently dropped, not retried)
        with db_mod.db() as conn:
            events = conn.execute(
                "SELECT delivery_status FROM subscription_events WHERE subscription_id=?",
                (sub["id"],),
            ).fetchall()
        assert len(events) == 1
        assert events[0]["delivery_status"] == "delivered"

    def test_event_delivered_normally_without_tombstone(self, client: TestClient) -> None:
        """Sanity check: without a tombstone the webhook IS called."""
        tc_mod.invalidate()

        _create_subscription(client)
        _insert_fact(client)

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("stigmem_node.subscription_delivery.httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.__enter__ = MagicMock(return_value=mock_inst)
            mock_inst.__exit__ = MagicMock(return_value=False)
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value = mock_inst

            _drain_subscription_delivery()

            mock_inst.post.assert_called_once()

    def test_only_tombstoned_entity_suppressed(self, client: TestClient) -> None:
        """Tombstone on Alice should not suppress Bob's events."""
        _ALICE = "stigmem://test/agent/alice"
        _BOB = "stigmem://test/agent/bob"

        _create_subscription(client, target="local")
        _insert_fact(client, entity=_ALICE, value="Alice")
        _insert_fact(client, entity=_BOB, value="Bob")

        _insert_tombstone(_ALICE)
        tc_mod.invalidate()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("stigmem_node.subscription_delivery.httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.__enter__ = MagicMock(return_value=mock_inst)
            mock_inst.__exit__ = MagicMock(return_value=False)
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value = mock_inst

            _drain_subscription_delivery()

            # Exactly one call — Bob's event; Alice's is suppressed
            assert mock_inst.post.call_count == 1
            call_body = mock_inst.post.call_args.kwargs.get("json") or mock_inst.post.call_args[
                1
            ].get("json", {})
            assert call_body.get("fact", {}).get("entity") == _BOB

    def test_tombstone_cache_invalidate_forces_recheck(self, client: TestClient) -> None:
        """After revocation (cache invalidation), delivery resumes for that entity."""
        _create_subscription(client)
        _insert_fact(client)

        tomb_id = _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        # Revoke the tombstone so entity is no longer tombstoned
        _revoke_tombstone(tomb_id)

        tc_mod.invalidate()

        mock_resp = MagicMock()
        mock_resp.status_code = 200

        with patch("stigmem_node.subscription_delivery.httpx.Client") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.__enter__ = MagicMock(return_value=mock_inst)
            mock_inst.__exit__ = MagicMock(return_value=False)
            mock_inst.post.return_value = mock_resp
            mock_cls.return_value = mock_inst

            _drain_subscription_delivery()

            # Revocation → entity no longer tombstoned → webhook called
            mock_inst.post.assert_called_once()


# ---------------------------------------------------------------------------
# §23.3.2 r.3 — recall suppression (about_entity)
# ---------------------------------------------------------------------------


class TestTombstoneRecallSuppression:
    def test_tombstoned_entity_absent_from_recall(self, client: TestClient) -> None:
        """Facts for tombstoned entity are excluded from recall results."""
        _insert_fact(client, entity=_ENTITY, value="alice remember me")

        # Sanity: fact returned before tombstone
        tc_mod.invalidate()
        facts_before = _recall(client, query="alice remember me")
        entity_uris_before = {f["fact"]["entity"] for f in facts_before}
        assert _ENTITY in entity_uris_before

        _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        facts_after = _recall(client, query="alice remember me")
        entity_uris_after = {f["fact"]["entity"] for f in facts_after}
        assert _ENTITY not in entity_uris_after

    def test_non_tombstoned_entity_still_returned(self, client: TestClient) -> None:
        """Tombstoning Alice does not suppress Bob's facts in recall."""
        _ALICE = "stigmem://test/agent/alice"
        _BOB = "stigmem://test/agent/bob"

        _insert_fact(client, entity=_ALICE, value="alice xyz")
        _insert_fact(client, entity=_BOB, value="bob xyz")

        _insert_tombstone(_ALICE)
        tc_mod.invalidate()

        facts = _recall(client, query="bob xyz")
        entity_uris = {f["fact"]["entity"] for f in facts}
        assert _BOB in entity_uris
        assert _ALICE not in entity_uris

    def test_tombstone_revocation_restores_recall(self, client: TestClient) -> None:
        """After tombstone revocation, entity facts reappear in recall."""
        _insert_fact(client, entity=_ENTITY, value="alice revoked")

        tomb_id = _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        # Confirm suppressed
        assert not any(
            f["fact"]["entity"] == _ENTITY for f in _recall(client, query="alice revoked")
        )

        # Revoke tombstone
        _revoke_tombstone(tomb_id)

        tc_mod.invalidate()

        facts = _recall(client, query="alice revoked")
        assert any(f["fact"]["entity"] == _ENTITY for f in facts)

    def test_tombstone_revocation_restores_only_revoked_entity(
        self, client: TestClient
    ) -> None:
        """Revoking Alice's tombstone must not restore Bob while Bob remains tombstoned."""
        alice = "stigmem://test/agent/alice-revoked-only"
        bob = "stigmem://test/agent/bob-still-tombstoned"
        _insert_fact(client, entity=alice, value="selective restore alpha")
        _insert_fact(client, entity=bob, value="selective restore beta")

        alice_tomb = _insert_tombstone(alice)
        _insert_tombstone(bob)
        tc_mod.invalidate()

        _revoke_tombstone(alice_tomb)
        tc_mod.invalidate()

        facts = _recall(client, query="selective restore")
        entities = {sf["fact"]["entity"] for sf in facts}
        assert alice in entities
        assert bob not in entities

    def test_tombstone_suppresses_total_scored_header(self, client: TestClient) -> None:
        """§23.3.3 r.3: X-Total-Count header must be absent when tombstone filtering was applied."""
        _insert_fact(client, entity=_ENTITY, value="oracle leak test")

        tc_mod.invalidate()
        resp_before = client.post(
            "/v1/recall",
            json={
                "query": "oracle leak test",
                "scope": "local",
                "token_budget": 4000,
                "include_neighbors": False,
            },
        )
        assert resp_before.status_code == 200
        assert "X-Total-Count" in resp_before.headers
        assert resp_before.json()["total_scored"] is not None

        _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        resp_after = client.post(
            "/v1/recall",
            json={
                "query": "oracle leak test",
                "scope": "local",
                "token_budget": 4000,
                "include_neighbors": False,
            },
        )
        assert resp_after.status_code == 200
        assert "X-Total-Count" not in resp_after.headers
        assert resp_after.json()["total_scored"] is None

    def test_card_fastpath_tombstoned_entity_excluded(self, client: TestClient) -> None:
        """Card fast-path: synthetic card for tombstoned about_entity is not returned."""
        # Insert multiple facts to ensure a card gets materialised
        for i in range(3):
            _insert_fact(client, entity=_ENTITY, value=f"card-fact-{i}")

        # Prime a fresh card via the cards endpoint
        client.get(f"/v1/cards/{_ENTITY}?scope=local")

        _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        facts = _recall(client, query="card-fact")
        # No fact — neither raw nor card-synthetic — should reference the tombstoned entity
        for sf in facts:
            assert sf["fact"]["entity"] != _ENTITY
            assert not sf["fact"]["id"].startswith(f"card:{_ENTITY}")


# ---------------------------------------------------------------------------
# §23.3.3 r.3 — oracle leakage: pagination totals suppressed after tombstone
# ---------------------------------------------------------------------------


class TestTombstonePaginationOracleLeakage:
    """X-Total-Count and total/total_scored must not leak tombstone information."""

    def test_facts_query_total_suppressed_after_tombstone(self, client: TestClient) -> None:
        """Facts query: total and X-Total-Count absent when tombstone filtering applied."""
        _insert_fact(client, entity=_ENTITY, value="oracle-facts")

        tc_mod.invalidate()
        resp_before = client.get("/v1/facts?scope=local")
        assert resp_before.status_code == 200
        assert "X-Total-Count" in resp_before.headers
        assert resp_before.json()["total"] is not None

        _insert_tombstone(_ENTITY)
        tc_mod.invalidate()

        resp_after = client.get("/v1/facts?scope=local")
        assert resp_after.status_code == 200
        assert "X-Total-Count" not in resp_after.headers
        assert resp_after.json()["total"] is None

    def test_facts_query_total_present_without_tombstone(self, client: TestClient) -> None:
        """Facts query: total and X-Total-Count present when no tombstone filtering."""
        _BOB = "stigmem://test/agent/bob-no-tombstone"
        _insert_fact(client, entity=_BOB, value="bob-facts-ok")

        tc_mod.invalidate()
        resp = client.get("/v1/facts?scope=local")
        assert resp.status_code == 200
        assert "X-Total-Count" in resp.headers
        assert resp.json()["total"] is not None
        assert resp.json()["total"] > 0

    def test_facts_query_revocation_restores_only_revoked_entity(
        self, client: TestClient
    ) -> None:
        """Facts query restores only the revoked tombstone target and keeps filtering others."""
        alice = "stigmem://test/agent/alice-facts-revoked"
        bob = "stigmem://test/agent/bob-facts-still-tombstoned"
        _insert_fact(client, entity=alice, value="facts selective restore alpha")
        _insert_fact(client, entity=bob, value="facts selective restore beta")

        alice_tomb = _insert_tombstone(alice)
        _insert_tombstone(bob)
        tc_mod.invalidate()
        _revoke_tombstone(alice_tomb)
        tc_mod.invalidate()

        resp = client.get("/v1/facts?scope=local")
        assert resp.status_code == 200
        entities = {fact["entity"] for fact in resp.json()["facts"]}
        assert alice in entities
        assert bob not in entities
        assert "X-Total-Count" not in resp.headers
        assert resp.json()["total"] is None

    def test_facts_query_legal_hold_non_admin_is_silent(self, client: TestClient) -> None:
        """Non-admin facts query must not expose legal-hold tombstone metadata."""
        entity = "stigmem://test/agent/legal-hold-silent"
        _insert_fact(client, entity=entity, value="legal hold silent")
        _insert_tombstone(entity, legal_hold=True)
        tc_mod.invalidate()

        resp = client.get("/v1/facts", params={"scope": "local", "entity": entity})
        assert resp.status_code == 200
        body = resp.json()
        assert body["facts"] == []
        assert body["tombstone_notices"] == []
        assert "X-Total-Count" not in resp.headers
        assert body["total"] is None
