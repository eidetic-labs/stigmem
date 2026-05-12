"""Recall benchmark harness — nDCG@10 + Recall@5 vs baseline.json."""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime
from typing import Any

import httpx

from .utils import (
    assert_fact,
    corpus_sha,
    do_recall,
    fact_id_from_item,
    load_baseline,
    load_probes,
    make_client,
    ndcg_at_k,
    recall_at_k,
)

_SERVER_VERSION = os.environ.get("STIGMEM_VERSION", "unknown")


# ---------------------------------------------------------------------------
# Corpus seeding
# ---------------------------------------------------------------------------

_SEED_FACTS = [
    # Entity-lookup & paraphrase facts
    ("user:alice", "memory:role", "admin"),
    ("user:bob", "memory:department", "engineering"),
    ("user:charlie", "memory:capability", "write"),
    ("user:diana", "memory:clearance", "top-secret"),
    ("user:eve", "memory:status", "active"),
    ("user:frank", "memory:team", "platform"),
    ("user:grace", "memory:manager", "user:frank"),
    ("agent:hal", "memory:trust_level", "0.9"),
    ("user:ivan", "memory:locale", "en-US"),
    ("user:julia", "memory:project", "stigmem"),
    ("org:acme", "memory:plan", "enterprise"),
    ("service:api", "memory:owner", "user:alice"),
    ("user:kate", "memory:role", "engineer"),
    ("user:leo", "memory:department", "security"),
    ("user:mia", "memory:status", "inactive"),
    ("agent:nova", "memory:trust_level", "0.7"),
    ("user:oscar", "memory:locale", "fr-FR"),
    ("user:petra", "memory:team", "frontend"),
    ("org:betacorp", "memory:plan", "starter"),
    ("service:db", "memory:owner", "user:kate"),
]


def seed_corpus(client: httpx.Client, ttl_facts: list[dict[str, Any]]) -> dict[str, str]:
    """Assert all seed facts; return entity+relation → fact_id mapping."""
    fact_id_map: dict[str, str] = {}
    for entity, relation, value in _SEED_FACTS:
        resp = assert_fact(
            client,
            entity=entity,
            relation=relation,
            value={"type": "string", "v": value},
            source="eval:recall-harness",
            confidence=1.0,
            scope="local",
        )
        fact_id_map[f"{entity}#{relation}"] = resp.get("id", "")

    # Seed TTL-expiring facts (for probes with subclass=ttl_expiring)
    for probe in ttl_facts:
        entity = probe.get("gold_entity", "")
        relation = probe.get("gold_relation", "")
        value = probe.get("gold_value", "test")
        ttl = probe.get("ttl_seconds", 5)
        if entity and relation:
            resp = assert_fact(
                client,
                entity=entity,
                relation=relation,
                value={"type": "string", "v": value},
                source="eval:recall-harness",
                confidence=1.0,
                scope="local",
                ttl_seconds=ttl,
            )
            fact_id_map[f"{entity}#{relation}"] = resp.get("id", "")

    return fact_id_map


# ---------------------------------------------------------------------------
# Probe evaluation
# ---------------------------------------------------------------------------


def evaluate_probe(
    client: httpx.Client,
    probe: dict[str, Any],
    fact_id_map: dict[str, str],
) -> dict[str, Any]:
    query = probe["query"]
    probe_class = probe["class"]
    subclass = probe.get("subclass", "")

    # Retrieve ranked facts via recall
    ranked_items = do_recall(client, query, scope="local", limit=20)
    ranked_ids = [fact_id_from_item(item) for item in ranked_items]

    # Build the relevant set from the id map
    relevant_ids: set[str] = set()
    if probe_class in ("entity_lookup", "paraphrase"):
        entity = probe.get("gold_entity", "")
        relation = probe.get("gold_relation", "")
        key = f"{entity}#{relation}"
        fid = fact_id_map.get(key, "")
        if fid:
            relevant_ids.add(fid)
    elif probe_class == "relation_lookup":
        relation = probe.get("gold_relation", "")
        primary_entity = probe.get("gold_primary_entity", "")
        key = f"{primary_entity}#{relation}"
        fid = fact_id_map.get(key, "")
        if fid:
            relevant_ids.add(fid)
    elif probe_class == "adversarial_ood":
        if subclass == "ttl_expiring":
            entity = probe.get("gold_entity", "")
            relation = probe.get("gold_relation", "")
            fid = fact_id_map.get(f"{entity}#{relation}", "")
            if fid:
                relevant_ids.add(fid)
        # entity_not_in_corpus, out_of_domain: relevant_ids stays empty

    ndcg = ndcg_at_k(ranked_ids, relevant_ids, k=10)
    rec5 = recall_at_k(ranked_ids, relevant_ids, k=5)

    return {
        "probe_id": probe["id"],
        "class": probe_class,
        "subclass": subclass,
        "query": query,
        "ndcg_at_10": ndcg,
        "recall_at_5": rec5,
        "relevant_ids": list(relevant_ids),
        "ranked_ids": ranked_ids[:10],
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def run(
    base_url: str | None = None,
    api_key: str | None = None,
    save_baseline: bool = False,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    if client is None:
        client = make_client(
            base_url=base_url or os.environ.get("STIGMEM_EVAL_URL") or "http://127.0.0.1:8765",
            api_key=api_key or os.environ.get("STIGMEM_EVAL_API_KEY", ""),
        )
    probes = load_probes()
    ttl_probes = [p for p in probes if p.get("subclass") == "ttl_expiring"]
    sha = corpus_sha(probes)

    # Seed corpus
    fact_id_map = seed_corpus(client, ttl_probes)

    t0 = time.monotonic()
    probe_results: list[dict[str, Any]] = []
    for probe in probes:
        result = evaluate_probe(client, probe, fact_id_map)
        probe_results.append(result)
    elapsed = time.monotonic() - t0

    ndcg_scores = [r["ndcg_at_10"] for r in probe_results]
    rec5_scores = [r["recall_at_5"] for r in probe_results]

    mean_ndcg = sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0
    mean_rec5 = sum(rec5_scores) / len(rec5_scores) if rec5_scores else 0.0

    # Regression check
    regression = {"triggered": False, "delta_pct": 0.0, "threshold_pct": 3.0}
    try:
        baseline = load_baseline()
        baseline_ndcg = baseline.get("nDCG@10", 0.0)
        if baseline_ndcg > 0:
            delta_pct = (baseline_ndcg - mean_ndcg) / baseline_ndcg * 100.0
            regression = {
                "triggered": delta_pct >= 3.0,
                "delta_pct": round(delta_pct, 4),
                "threshold_pct": 3.0,
                "baseline_ndcg": baseline_ndcg,
                "current_ndcg": mean_ndcg,
            }
    except FileNotFoundError:
        regression["note"] = "no baseline.json found — skipping regression check"

    report: dict[str, Any] = {
        "type": "recall",
        "nDCG@10": round(mean_ndcg, 6),
        "Recall@5": round(mean_rec5, 6),
        "corpus_sha": sha,
        "server_version": _SERVER_VERSION,
        "probe_count": len(probes),
        "elapsed_s": round(elapsed, 3),
        "regression": regression,
        "probe_results": probe_results,
    }

    if save_baseline:
        import pathlib

        baseline_doc = {
            "nDCG@10": round(mean_ndcg, 6),
            "Recall@5": round(mean_rec5, 6),
            "corpus_sha": sha,
            "server_version": _SERVER_VERSION,
            "recorded_at": datetime.now(UTC).isoformat(),
        }
        bl_path = (
            pathlib.Path(__file__).resolve().parent.parent / "corpus" / "recall" / "baseline.json"
        )
        bl_path.write_text(json.dumps(baseline_doc, indent=2))

    return report


if __name__ == "__main__":
    import sys

    save = "--save-baseline" in sys.argv
    report = run(save_baseline=save)
    print(json.dumps(report, indent=2))
    triggered = report["regression"].get("triggered", False)
    sys.exit(1 if triggered else 0)
