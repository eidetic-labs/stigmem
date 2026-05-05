"""Shared utilities: HTTP client, corpus loader, metric helpers."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any

import httpx

EVAL_DIR = Path(__file__).resolve().parent.parent
CORPUS_DIR = EVAL_DIR / "corpus"
RESULTS_DIR = EVAL_DIR / "results"

DEFAULT_BASE_URL = os.environ.get("STIGMEM_EVAL_URL", "http://127.0.0.1:8765")
DEFAULT_API_KEY = os.environ.get("STIGMEM_EVAL_API_KEY", "")


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


def make_client(base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY) -> httpx.Client:
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return httpx.Client(base_url=base_url, headers=headers, timeout=30.0)


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_adversarial_class(class_name: str) -> list[dict[str, Any]]:
    """Load all scenario JSON files from corpus/adversarial/<class_name>/."""
    class_dir = CORPUS_DIR / "adversarial" / class_name
    scenarios: list[dict[str, Any]] = []
    for path in sorted(class_dir.glob("*.json")):
        with path.open() as f:
            data = json.load(f)
        if isinstance(data, list):
            scenarios.extend(data)
        else:
            scenarios.append(data)
    return scenarios


def load_all_adversarial() -> dict[str, list[dict[str, Any]]]:
    classes = [
        "typo_squatted",
        "contradiction_floods",
        "tombstone_bypass",
        "capability_token",
        "sanitizer_bypass",
    ]
    return {c: load_adversarial_class(c) for c in classes}


def load_probes() -> list[dict[str, Any]]:
    path = CORPUS_DIR / "recall" / "probes.json"
    with path.open() as f:
        return json.load(f)


def load_baseline() -> dict[str, Any]:
    path = CORPUS_DIR / "recall" / "baseline.json"
    with path.open() as f:
        return json.load(f)


def corpus_sha(probes: list[dict[str, Any]]) -> str:
    raw = json.dumps(probes, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Recall metrics
# ---------------------------------------------------------------------------


def fact_id_from_item(item: dict[str, Any]) -> str:
    """Extract fact ID from a recall result item (handles nested fact structure)."""
    return item.get("fact", item).get("id", "")


def ndcg_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int = 10) -> float:
    """nDCG@k — binary relevance, log2 discount."""
    def dcg(ids: list[str]) -> float:
        score = 0.0
        for i, id_ in enumerate(ids[:k], start=1):
            if id_ in relevant_ids:
                score += 1.0 / math.log2(i + 1)
        return score

    actual = dcg(ranked_ids)
    ideal_ids = list(relevant_ids)[:k]
    ideal = dcg(ideal_ids)
    return actual / ideal if ideal > 0 else 0.0


def recall_at_k(ranked_ids: list[str], relevant_ids: set[str], k: int = 5) -> float:
    """Recall@k — fraction of relevant facts appearing in top-k."""
    if not relevant_ids:
        return 0.0
    hits = sum(1 for id_ in ranked_ids[:k] if id_ in relevant_ids)
    return hits / len(relevant_ids)


# ---------------------------------------------------------------------------
# Recall API helper
# ---------------------------------------------------------------------------


def do_recall(
    client: httpx.Client,
    query: str,
    scope: str = "local",
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Return ranked recall result items.

    Each item has shape: {"fact": {...fact_record...}, "score_breakdown": {...}, ...}
    Use item["fact"]["id"] for the fact ID and item["score_breakdown"] for scores.
    """
    r = client.post(
        "/v1/recall",
        json={
            "query": query,
            "scope": scope,
            "token_budget": 8000,
            "depth": 2,
            "limit": limit,
        },
    )
    if r.status_code != 200:
        return []
    return r.json().get("facts", [])


# ---------------------------------------------------------------------------
# Fact assertion helper
# ---------------------------------------------------------------------------


def assert_fact(
    client: httpx.Client,
    entity: str,
    relation: str,
    value: Any,
    source: str = "eval:harness",
    confidence: float = 1.0,
    scope: str = "local",
    ttl_seconds: int | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "entity": entity,
        "relation": relation,
        "value": {"type": "string", "v": str(value)} if not isinstance(value, dict) else value,
        "source": source,
        "confidence": confidence,
        "scope": scope,
    }
    if ttl_seconds is not None:
        from datetime import UTC, datetime, timedelta
        payload["valid_until"] = (
            datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        ).isoformat()
    r = client.post("/v1/facts", json=payload)
    return r.json() if r.status_code in (200, 201) else {}
