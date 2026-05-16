"""Runtime monitoring and metric probes for the federation soak harness."""

from __future__ import annotations

import sys
import threading
import time
import uuid

import httpx

from . import state as metrics


def _assert_fact(
    client: httpx.Client,
    entity: str,
    relation: str,
    value: str,
    scope: str = "public",
    source: str = "eval:soak",
    confidence: float = 0.9,
) -> str:
    """Assert a fact; return fact_id or empty string on failure."""
    r = client.post(
        "/v1/facts",
        json={
            "entity": entity,
            "relation": relation,
            "value": {"type": "string", "v": value},
            "source": source,
            "confidence": confidence,
            "scope": scope,
        },
    )
    if r.status_code in (200, 201):
        return r.json().get("id", "")
    return ""


def _poll_fact(client: httpx.Client, fact_id: str, timeout_s: float = 30.0) -> float | None:
    """Poll GET /v1/facts/{fact_id} until visible; return lag_ms or None on timeout."""
    deadline = time.monotonic() + timeout_s
    last_error: httpx.HTTPError | None = None
    while time.monotonic() < deadline:
        try:
            r = client.get(f"/v1/facts/{fact_id}")
            if r.status_code == 200:
                return (time.monotonic() - (deadline - timeout_s)) * 1000  # approximate
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.5)
    if last_error is not None:
        print(
            f"  fact {fact_id} did not become visible; last poll error: {last_error}",
            file=sys.stderr,
        )
    return None


def _probe_replication(
    client_a: httpx.Client,
    clients: dict[str, httpx.Client],
) -> str:
    """Assert a probe fact on node-A; measure propagation to B and C. Returns fact_id."""

    entity = f"stigmem://eval/probe/{uuid.uuid4()}"
    relation = "eval:probe-value"
    value = str(uuid.uuid4())

    t0 = time.monotonic()
    fact_id = _assert_fact(client_a, entity, relation, value, scope="public")
    if not fact_id:
        return ""

    with metrics._lock:
        metrics._probe_count += 1
        metrics._audit_facts_sent += 1

    # Measure propagation to each peer in a thread
    def measure(target_name: str, target_client: httpx.Client) -> None:
        deadline = time.monotonic() + 30.0
        last_error: httpx.HTTPError | None = None
        while time.monotonic() < deadline:
            try:
                r = target_client.get(f"/v1/facts/{fact_id}")
                if r.status_code == 200:
                    lag_ms = (time.monotonic() - t0) * 1000
                    metrics._record_lag(target_name, lag_ms)
                    if target_name == "node-b":
                        with metrics._lock:
                            metrics._audit_facts_received += 1
                    return
            except httpx.HTTPError as exc:
                last_error = exc
            time.sleep(0.5)
        # Timeout — fact never appeared; log as max-timeout sample
        if last_error is not None:
            print(
                "  replication probe "
                f"{fact_id} to {target_name} timed out; last poll error: {last_error}",
                file=sys.stderr,
            )
        metrics._record_lag(target_name, 30_000.0)

    threads = []
    for name, client in clients.items():
        if name == "node-a":
            continue
        t = threading.Thread(target=measure, args=(name, client), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=35.0)

    return fact_id


def _verify_cap_token(client: httpx.Client, fact_id: str, valid_key: str) -> None:
    """
    Capability-token verification probe (H-SEC-2):
    - Attempt with a FORGED token → must return 401/403 (no partial data)
    - Attempt with the valid key → must return 200

    Updates global metrics._cap_token_total / metrics._cap_token_verified counters.
    """
    base_url = str(client.base_url).rstrip("/")

    # Attempt with invalid / forged bearer token
    forged = "eval.forged.token.invalid"
    try:
        r = httpx.get(
            f"{base_url}/v1/facts/{fact_id}",
            headers={"Authorization": f"Bearer {forged}"},
            timeout=10.0,
        )
        with metrics._lock:
            metrics._cap_token_total += 1
            if r.status_code in (401, 403):
                # Correct — access was properly denied
                metrics._cap_token_verified += 1
            # 200 here = security regression (bypass)
    except httpx.HTTPError as exc:
        with metrics._lock:
            metrics._cap_token_total += 1
        print(f"  forged-token probe failed before authorization decision: {exc}", file=sys.stderr)

    # Attempt with valid key — must succeed
    try:
        r = httpx.get(
            f"{base_url}/v1/facts/{fact_id}",
            headers={"Authorization": f"Bearer {valid_key}"},
            timeout=10.0,
        )
        with metrics._lock:
            metrics._cap_token_total += 1
            if r.status_code == 200:
                metrics._cap_token_verified += 1
    except httpx.HTTPError as exc:
        with metrics._lock:
            metrics._cap_token_total += 1
        print(f"  valid-token probe failed before authorization decision: {exc}", file=sys.stderr)


def check_audit_completeness(
    clients: dict[str, httpx.Client],
    sent_fact_ids: list[str],
) -> float:
    """
    Ratio: (facts from node-A visible on node-B) / total_asserted_on_A.
    Uses GET /v1/facts/{id} on node-B for each tracked probe fact_id.
    """
    if not sent_fact_ids:
        return 1.0

    found = 0
    for fid in sent_fact_ids:
        try:
            r = clients["node-b"].get(f"/v1/facts/{fid}")
            if r.status_code == 200:
                found += 1
        except httpx.HTTPError as exc:
            print(f"  audit completeness probe for {fid} failed: {exc}", file=sys.stderr)
    return found / len(sent_fact_ids)
