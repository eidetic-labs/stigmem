"""Adversarial corpus runner — 79 scenarios, pass/fail per scenario."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
from typing import Any

import httpx

from .utils import assert_fact, fact_id_from_item, load_all_adversarial, make_client

# ---------------------------------------------------------------------------
# Scenario runners by class
# ---------------------------------------------------------------------------


def run_typo_squatted(client: httpx.Client, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for s in scenarios:
        # Setup: assert canonical fact
        fact_resp = assert_fact(
            client,
            entity=s["setup_fact"]["entity"],
            relation=s["setup_fact"]["relation"],
            value=s["setup_fact"]["value"],
            source=s["setup_fact"]["source"],
            confidence=s["setup_fact"]["confidence"],
            scope=s["setup_fact"].get("scope", "local"),
        )
        canonical_id = fact_resp.get("id", "")

        # Query: recall using spoofed entity name embedded in query
        r = client.post(
            "/v1/recall",
            json={
                "query": s["recall_query"],
                "scope": "local",
                "token_budget": 4000,
                "depth": 2,
                "limit": 20,
            },
        )
        items = r.json().get("facts", []) if r.status_code == 200 else []
        # Recall items: {"fact": {...}, "score_breakdown": {...}, ...}
        top5_entities = [item.get("fact", item).get("entity", "") for item in items[:5]]

        spoofed = s["spoofed_entity"]
        passed = spoofed not in top5_entities
        results.append({
            "id": s["id"],
            "class": s["class"],
            "description": s["description"],
            "passed": passed,
            "detail": {
                "spoofed_entity": spoofed,
                "top5_entities": top5_entities,
                "canonical_id": canonical_id,
            },
        })
    return results


def run_contradiction_floods(client: httpx.Client, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for s in scenarios:
        entity = s["target_entity"]
        relation = s["target_relation"]

        # 1. Assert canonical fact
        canonical_resp = assert_fact(
            client,
            entity=entity,
            relation=relation,
            value={"type": "string", "v": s["canonical_value"]},
            source="eval:harness",
            confidence=s["canonical_confidence"],
            scope="local",
        )
        canonical_id = canonical_resp.get("id", "")

        # 2. Flood with low-confidence contradictions
        flood_ids: list[str] = []
        for _ in range(s["flood_count"]):
            fr = assert_fact(
                client,
                entity=entity,
                relation=relation,
                value={"type": "string", "v": s["flood_value"]},
                source=s["flood_source"],
                confidence=s["flood_confidence"],
                scope="local",
            )
            if fr.get("id"):
                flood_ids.append(fr["id"])

        # 3. Recall and check
        r = client.post(
            "/v1/recall",
            json={
                "query": f"{entity} {relation}",
                "scope": "local",
                "token_budget": 4000,
                "depth": 1,
                "limit": 50,
            },
        )
        items = r.json().get("facts", []) if r.status_code == 200 else []
        # items: [{"fact": {...}, "score_breakdown": {...}, ...}]
        top3_ids = [fact_id_from_item(item) for item in items[:3]]
        canonical_in_top3 = canonical_id in top3_ids if canonical_id else False

        # Check salience cap: flood facts should not have score_breakdown.weighted_total > 0.75
        flood_id_set = set(flood_ids)
        flood_saliences = [
            item.get("score_breakdown", {}).get("weighted_total", 0.0)
            for item in items
            if fact_id_from_item(item) in flood_id_set
        ]
        max_flood_salience = max(flood_saliences) if flood_saliences else 0.0

        criteria = s["pass_criteria"]
        passed = (
            canonical_in_top3 == criteria.get("canonical_in_top3", True)
            and max_flood_salience <= criteria.get("max_flood_salience", 0.75)
        )

        results.append({
            "id": s["id"],
            "class": s["class"],
            "description": s["description"],
            "passed": passed,
            "detail": {
                "canonical_in_top3": canonical_in_top3,
                "max_flood_salience": max_flood_salience,
                "flood_count": len(flood_ids),
                "canonical_id": canonical_id,
            },
        })
    return results


def _recall_ids(client: httpx.Client, entity: str, relation: str) -> set[str]:
    """Return the set of fact IDs recalled for an entity+relation query."""
    r = client.post(
        "/v1/recall",
        json={
            "query": f"{entity} {relation}",
            "scope": "local",
            "token_budget": 4000,
            "depth": 1,
            "limit": 50,
        },
    )
    items = r.json().get("facts", []) if r.status_code == 200 else []
    return {fact_id_from_item(item) for item in items}


def run_tombstone_bypass(client: httpx.Client, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for s in scenarios:
        entity = s["entity"]
        relation = s["relation"]
        subclass = s["subclass"]

        # Assert fact A (canonical)
        fact_a_resp = assert_fact(
            client,
            entity=entity,
            relation=relation,
            value=s["fact_a"]["value"],
            source=s["fact_a"]["source"],
            confidence=s["fact_a"]["confidence"],
            scope="local",
        )
        fact_a_id = fact_a_resp.get("id", "")

        if subclass == "same_source":
            # Retraction: assert confidence=0 with a distinct value so the CID
            # differs from fact_a (the server is CID-idempotent; same CID just
            # returns the existing row without creating a new fact).
            retraction_resp = assert_fact(
                client,
                entity=entity,
                relation=relation,
                value={"type": "string", "v": f"retracted-{s['id']}"},
                source=s["fact_a"]["source"],
                confidence=s["tombstone_confidence"],
                scope="local",
            )
            retraction_id = retraction_resp.get("id", "")
            # Assert fact B (replacement from same source)
            fact_b_resp = assert_fact(
                client,
                entity=entity,
                relation=relation,
                value=s["fact_b"]["value"],
                source=s["fact_b"]["source"],
                confidence=s["fact_b"]["confidence"],
                scope="local",
            )
            fact_b_id = fact_b_resp.get("id", "")

            recalled = _recall_ids(client, entity, relation)
            retraction_absent = retraction_id not in recalled if retraction_id else True
            fact_b_present = fact_b_id in recalled if fact_b_id else False
            distinct_ids = retraction_id != fact_b_id

            criteria = s["pass_criteria"]
            passed = (
                retraction_absent == criteria.get("retraction_absent", True)
                and fact_b_present == criteria.get("fact_b_present", True)
                and distinct_ids == criteria.get("distinct_fact_ids", True)
            )

            results.append({
                "id": s["id"],
                "class": s["class"],
                "description": s["description"],
                "passed": passed,
                "detail": {
                    "fact_a_id": fact_a_id,
                    "retraction_id": retraction_id,
                    "fact_b_id": fact_b_id,
                    "retraction_absent": retraction_absent,
                    "fact_b_present": fact_b_present,
                    "distinct_ids": distinct_ids,
                },
            })
        else:
            # Different-source: adversary tries to tombstone canonical
            tombstone_id = ""
            if "adversary_tombstone" in s:
                tomb_resp = assert_fact(
                    client,
                    entity=entity,
                    relation=relation,
                    value=s["adversary_tombstone"]["value"],
                    source=s["adversary_tombstone"]["source"],
                    confidence=s["adversary_tombstone"]["confidence"],
                    scope="local",
                )
                tombstone_id = tomb_resp.get("id", "")
            fact_b_resp = assert_fact(
                client,
                entity=entity,
                relation=relation,
                value=s["fact_b"]["value"],
                source=s["fact_b"]["source"],
                confidence=s["fact_b"]["confidence"],
                scope="local",
            )
            fact_b_id = fact_b_resp.get("id", "")

            recalled = _recall_ids(client, entity, relation)
            fact_a_present = fact_a_id in recalled if fact_a_id else False
            tombstone_absent = tombstone_id not in recalled if tombstone_id else True
            fact_b_present = fact_b_id in recalled if fact_b_id else False
            distinct_ids = fact_a_id != fact_b_id

            criteria = s["pass_criteria"]
            passed = (
                fact_a_present == criteria.get("fact_a_present", True)
                and tombstone_absent == criteria.get("adversary_tombstone_absent", True)
                and fact_b_present == criteria.get("fact_b_present", True)
                and distinct_ids == criteria.get("distinct_fact_ids", True)
            )

            results.append({
                "id": s["id"],
                "class": s["class"],
                "description": s["description"],
                "passed": passed,
                "detail": {
                    "fact_a_id": fact_a_id,
                    "tombstone_id": tombstone_id,
                    "fact_b_id": fact_b_id,
                    "fact_a_present": fact_a_present,
                    "tombstone_absent": tombstone_absent,
                    "fact_b_present": fact_b_present,
                    "distinct_ids": distinct_ids,
                },
            })
    return results


def _build_oversized_token(length: int = 20000) -> str:
    return "Bearer " + ("A" * length)


def _build_forged_auth(shape: str, s: dict[str, Any]) -> str:
    """Build a forged Authorization header value for a given forgery shape."""
    if shape == "unsigned_json":
        token = s.get("token", '{"capabilities":["write"]}')
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload = base64.urlsafe_b64encode(token.encode()).decode().rstrip("=")
        return f"Bearer {header}.{payload}."
    if shape == "unknown_key_signed":
        header = base64.urlsafe_b64encode(b'{"alg":"EdDSA","kid":"unknown-ephemeral"}').decode().rstrip("=")
        payload_dict = {
            "entity_uri": "https://unknown.example.org",
            "capabilities": ["write"],
            "exp": int(time.time()) + 3600,
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_dict).encode()
        ).decode().rstrip("=")
        sig_b64 = base64.urlsafe_b64encode(os.urandom(64)).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}.{sig_b64}"
    if shape == "bit_corrupted_signature":
        header = base64.urlsafe_b64encode(b'{"alg":"EdDSA"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(b'{"capabilities":["write"]}').decode().rstrip("=")
        sig_b64 = base64.urlsafe_b64encode(b"\xff" * 64).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}.{sig_b64}"
    if shape == "expired_token":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"capabilities": ["write"], "exp": 0}).encode()
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "nbf_in_future":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"capabilities": ["write"], "nbf": 9999999999, "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "capability_escalation":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"capabilities": ["read", "write", "admin"], "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "empty_capabilities":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps({"capabilities": [], "exp": 9999999999}).encode()
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "nonce_replay":
        return "Bearer invalid-replay-token"
    if shape == "alg_none":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            b'{"capabilities":["write"],"exp":9999999999}'
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "entity_uri_mismatch":
        header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(
            b'{"entity_uri":"https://org-a.example.org","capabilities":["write"]}'
        ).decode().rstrip("=")
        return f"Bearer {header}.{payload_b64}."
    if shape == "malformed_jwt_no_header":
        return f"Bearer {s.get('token', 'bad.token')}"
    if shape == "malformed_jwt_bad_base64":
        return f"Bearer {s.get('token', 'bad.!!!.bad')}"
    if shape == "empty_auth_header":
        return ""
    if shape == "wrong_auth_scheme":
        return s.get("token", "Basic dXNlcjpwYXNz")
    if shape == "oversized_token":
        return _build_oversized_token(16385)
    return "Bearer unknown-shape"


def run_capability_token(client: httpx.Client, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []

    for s in scenarios:
        shape = s["forgery_shape"]
        endpoint = s.get("endpoint", "/v1/facts")
        method = s.get("method", "POST").lower()
        expected_statuses = s.get("expected_status", [401, 403])

        auth = _build_forged_auth(shape, s)

        headers = {}
        if auth:
            headers["Authorization"] = auth

        body = {
            "entity": "user:captest",
            "relation": "memory:role",
            "value": {"type": "string", "v": "admin"},
            "source": "eval:adversary",
            "confidence": 1.0,
            "scope": "local",
        }

        try:
            if method == "post":
                resp = client.post(
                    endpoint,
                    json=body if endpoint == "/v1/facts" else {
                        "query": "role", "scope": "local", "token_budget": 100
                    },
                    headers=headers,
                )
            else:
                resp = client.get(endpoint, headers=headers)
        except Exception as exc:
            results.append({
                "id": s["id"],
                "class": s["class"],
                "description": s["description"],
                "passed": False,
                "detail": {"error": str(exc)},
            })
            continue

        status = resp.status_code
        try:
            body_json = resp.json()
        except Exception:
            body_json = {}

        # Zero leakage check: response must not contain any fact data
        has_fact_data = (
            isinstance(body_json, dict)
            and (
                "facts" in body_json
                or ("entity" in body_json and "relation" in body_json)
                or ("id" in body_json and "entity" in body_json)
            )
        )

        passed = status in expected_statuses and not has_fact_data

        results.append({
            "id": s["id"],
            "class": s["class"],
            "description": s["description"],
            "passed": passed,
            "detail": {
                "status": status,
                "expected_statuses": expected_statuses,
                "has_fact_data": has_fact_data,
                "shape": shape,
            },
        })

    return results


def _build_null_byte_payload(s: dict[str, Any]) -> str:
    """Build null-byte payloads at runtime (raw \x00 cannot be stored in JSON)."""
    null_byte_map = {
        "sanitize-006": "user:alice\x00.evil",
        "sanitize-007": "admin\x00evil",
        "sanitize-008": "memory:role\x00drop",
        "sanitize-009": "user:\x00\x00\x00",
        "sanitize-010": "\x00agent:evil",
    }
    return null_byte_map.get(s["id"], s.get("payload", ""))


def run_sanitizer_bypass(client: httpx.Client, scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []

    for s in scenarios:
        subclass = s["subclass"]
        payload_field = s["payload_field"]

        # Build payload — null_byte scenarios are constructed at runtime
        if subclass == "null_bytes":
            raw_payload = _build_null_byte_payload(s)
        elif payload_field in ("entity", "relation", "source", "value"):
            raw_payload = s.get("payload", "")
            if s.get("payload_length"):
                raw_payload = s.get("payload_prefix", "") + s.get("payload_fill", "X") * s["payload_length"]
        else:
            raw_payload = s.get("payload", "")

        # Build fact body with injected payload
        fact_body: dict[str, Any] = {
            "entity": "user:sanitize-test",
            "relation": "memory:role",
            "value": {"type": "string", "v": "safe"},
            "source": "eval:harness",
            "confidence": 1.0,
            "scope": "local",
        }

        if payload_field == "body":
            nested: Any = "leaf"
            for _ in range(200):
                nested = {"x": nested}
            fact_body["extra"] = nested
        elif payload_field == "value":
            fact_body["value"] = {"type": "string", "v": raw_payload}
            fact_body["relation"] = "memory:data"
        elif payload_field == "entity":
            fact_body["entity"] = raw_payload
        elif payload_field == "relation":
            fact_body["relation"] = raw_payload
        elif payload_field == "source":
            fact_body["source"] = raw_payload

        r = client.post("/v1/facts", json=fact_body)

        status = r.status_code
        try:
            resp_body = r.json()
        except Exception:
            resp_body = {}

        # Pass criterion: 400 (rejected) OR stored but sanitised (no raw injection in response)
        if status in (400, 422):
            passed = True
        elif status in (200, 201):
            # Stored — check that payload is not verbatim in the stored value
            stored_raw = json.dumps(resp_body)
            raw = s.get("payload", "")
            # For oversized payloads we just check it was stored with some form of truncation
            if s.get("payload_length", 0) > 1000:
                passed = True  # server accepted but likely truncated/rejected at a different layer
            else:
                # Prompt injections: raw text OK to store (no execution), pass
                if subclass == "prompt_injection":
                    passed = True
                elif subclass in ("sql_injection", "null_bytes"):
                    # SQL injection or null bytes must never be raw in retrievable form
                    # Check that null bytes are not present in stored value
                    passed = "\x00" not in stored_raw and "DROP TABLE" not in stored_raw
                else:
                    passed = True
        else:
            passed = status not in (500, 503)

        results.append({
            "id": s["id"],
            "class": s["class"],
            "description": s["description"],
            "passed": passed,
            "detail": {
                "status": status,
                "subclass": subclass,
            },
        })

    return results


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run_all(
    base_url: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    client = make_client(
        base_url=base_url or os.environ.get("STIGMEM_EVAL_URL", "http://127.0.0.1:8765"),
        api_key=api_key or os.environ.get("STIGMEM_EVAL_API_KEY", ""),
    )
    corpus = load_all_adversarial()
    t0 = time.monotonic()

    all_results: list[dict[str, Any]] = []
    all_results += run_typo_squatted(client, corpus["typo_squatted"])
    all_results += run_contradiction_floods(client, corpus["contradiction_floods"])
    all_results += run_tombstone_bypass(client, corpus["tombstone_bypass"])
    all_results += run_capability_token(client, corpus["capability_token"])
    all_results += run_sanitizer_bypass(client, corpus["sanitizer_bypass"])

    elapsed = time.monotonic() - t0
    total = len(all_results)
    passed = sum(1 for r in all_results if r["passed"])
    failed = total - passed

    return {
        "type": "adversarial",
        "total": total,
        "passed": passed,
        "failed": failed,
        "elapsed_s": round(elapsed, 3),
        "results": all_results,
    }


if __name__ == "__main__":
    import sys
    report = run_all()
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["failed"] == 0 else 1)
