"""Regression test for issue #47 — concurrent ``deliver_pending`` and ``sweep_loop``.

Before migration 028 + the atomic-claim refactor, the delivery path was a
non-atomic SELECT (status='pending') + UPDATE (status='delivered').  Two
concurrent callers could observe the same row in their respective SELECTs
and each invoke the webhook, causing duplicate POSTs with the same
``event_id`` — exactly the flake reported in issue #47 against
``test_tombstone_filter.py``.

These tests assert the new atomic claim eliminates the race:

1. ``test_concurrent_deliver_pending_no_duplicate`` — many threads call
   ``deliver_pending`` in parallel.  Each event must deliver at most once.
2. ``test_sweep_loop_and_deliver_pending_no_duplicate`` — the background
   ``sweep_loop`` task runs alongside an explicit ``deliver_pending`` call.
3. ``test_stale_claim_recovered`` — an event that became stuck in
   ``delivering`` is reset to ``pending`` after the claim timeout.
"""

from __future__ import annotations

import asyncio
import threading
from collections import Counter
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import stigmem_node.db as db_mod
import stigmem_node.settings as settings_mod
from stigmem_node.subscription_delivery import deliver_pending, sweep_loop


def _make_subscription(client: TestClient) -> str:
    resp = client.post(
        "/v1/subscriptions",
        json={
            "target": "local",
            "on_change": "webhook",
            "delivery_address": "https://example.com/hook",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _insert_facts(client: TestClient, n: int) -> None:
    for i in range(n):
        resp = client.post(
            "/v1/facts",
            json={
                "entity": f"stigmem://test/agent/a{i}",
                "relation": "test:name",
                "value": {"type": "string", "v": f"agent-{i}"},
                "source": f"stigmem://test/agent/a{i}",
                "scope": "local",
            },
        )
        assert resp.status_code == 201, resp.text


def _patched_http_mock() -> tuple[MagicMock, MagicMock]:
    """Return (mock_class, mock_instance) wired for use with patch()."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    mock_inst = MagicMock()
    mock_inst.__enter__ = MagicMock(return_value=mock_inst)
    mock_inst.__exit__ = MagicMock(return_value=False)
    mock_inst.post.return_value = mock_resp

    mock_cls = MagicMock(return_value=mock_inst)
    return mock_cls, mock_inst


def test_concurrent_deliver_pending_no_duplicate(client: TestClient) -> None:
    """Many threads racing on ``deliver_pending`` must not duplicate-deliver."""
    _make_subscription(client)
    _insert_facts(client, n=20)

    mock_cls, mock_inst = _patched_http_mock()
    barrier = threading.Barrier(8)

    def worker() -> None:
        barrier.wait()  # release all threads simultaneously
        deliver_pending()

    with patch("stigmem_node.subscription_delivery.httpx.Client", mock_cls):
        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    # Every POSTed body carries the event_id; count distinct deliveries.
    event_ids = [call.kwargs["json"]["event_id"] for call in mock_inst.post.call_args_list]
    counts = Counter(event_ids)
    duplicates = {eid: c for eid, c in counts.items() if c > 1}
    assert duplicates == {}, f"events delivered more than once: {duplicates}"

    # All 20 events should be delivered exactly once.
    assert len(counts) == 20
    with db_mod.db() as conn:
        rows = conn.execute(
            "SELECT delivery_status, COUNT(*) AS n FROM subscription_events"
            " GROUP BY delivery_status"
        ).fetchall()
    status_counts = {r["delivery_status"]: r["n"] for r in rows}
    assert status_counts.get("delivered") == 20
    assert status_counts.get("delivering", 0) == 0
    assert status_counts.get("pending", 0) == 0


def test_sweep_loop_and_deliver_pending_no_duplicate(client: TestClient) -> None:
    """``sweep_loop`` running concurrently with an explicit deliver call."""
    _make_subscription(client)
    _insert_facts(client, n=10)

    mock_cls, mock_inst = _patched_http_mock()

    async def driver() -> None:
        # Force aggressive sweeping for the duration of this test.
        original_interval = settings_mod.settings.subscription_delivery_sweep_s
        settings_mod.settings.subscription_delivery_sweep_s = 0
        try:
            task = asyncio.create_task(sweep_loop())
            # Race the loop against an explicit call.
            await asyncio.gather(
                asyncio.to_thread(deliver_pending),
                asyncio.to_thread(deliver_pending),
                asyncio.sleep(0.05),
            )
            task.cancel()
            # gather(return_exceptions=True) absorbs the CancelledError
            # without re-raising; keeps the static analyzers happy and
            # avoids a bare `await task` that some linters flag as a
            # no-effect statement.
            await asyncio.gather(task, return_exceptions=True)
        finally:
            settings_mod.settings.subscription_delivery_sweep_s = original_interval

    with patch("stigmem_node.subscription_delivery.httpx.Client", mock_cls):
        asyncio.run(driver())

    event_ids = [call.kwargs["json"]["event_id"] for call in mock_inst.post.call_args_list]
    counts = Counter(event_ids)
    duplicates = {eid: c for eid, c in counts.items() if c > 1}
    assert duplicates == {}, f"events delivered more than once: {duplicates}"


def test_stale_claim_recovered(client: TestClient) -> None:
    """An event stuck in ``delivering`` past the timeout must be reclaimed."""
    sub_id = _make_subscription(client)
    _insert_facts(client, n=1)

    # Simulate a crashed worker: mark the only event as 'delivering' with an
    # old claimed_at well outside the configured timeout window.
    stale = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    with db_mod.db() as conn:
        conn.execute(
            "UPDATE subscription_events SET delivery_status='delivering', claimed_at=? "
            "WHERE subscription_id=?",
            (stale, sub_id),
        )

    mock_cls, mock_inst = _patched_http_mock()
    with patch("stigmem_node.subscription_delivery.httpx.Client", mock_cls):
        # Tighten the timeout so the stale row is definitely past the cutoff.
        original = settings_mod.settings.subscription_claim_timeout_s
        settings_mod.settings.subscription_claim_timeout_s = 60
        try:
            deliver_pending()
        finally:
            settings_mod.settings.subscription_claim_timeout_s = original

    # Recovery → reclaim → delivery, all in one call.
    assert mock_inst.post.call_count == 1
    with db_mod.db() as conn:
        row = conn.execute(
            "SELECT delivery_status, claimed_at FROM subscription_events "
            "WHERE subscription_id=?",
            (sub_id,),
        ).fetchone()
    assert row["delivery_status"] == "delivered"
    assert row["claimed_at"] is None


def test_claim_clears_after_failure_and_retry_is_pending(client: TestClient) -> None:
    """On webhook failure the row returns to 'pending' (not stuck 'delivering')."""
    sub_id = _make_subscription(client)
    _insert_facts(client, n=1)

    fail_resp = MagicMock()
    fail_resp.status_code = 503

    mock_inst = MagicMock()
    mock_inst.__enter__ = MagicMock(return_value=mock_inst)
    mock_inst.__exit__ = MagicMock(return_value=False)
    mock_inst.post.return_value = fail_resp
    mock_cls = MagicMock(return_value=mock_inst)

    with patch("stigmem_node.subscription_delivery.httpx.Client", mock_cls):
        deliver_pending()

    with db_mod.db() as conn:
        row = conn.execute(
            "SELECT delivery_status, delivery_attempts, next_retry_at, claimed_at "
            "FROM subscription_events WHERE subscription_id=?",
            (sub_id,),
        ).fetchone()
    assert row["delivery_status"] == "pending"
    assert row["delivery_attempts"] == 1
    assert row["next_retry_at"] is not None
    assert row["claimed_at"] is None
