"""Shared conformance test vectors — run against both stigmem-py and stigmem-ts.

Each vector is a plain dict so it can be JSON-serialised for cross-SDK use.
"""

from __future__ import annotations

ASSERT_VECTORS = [
    {
        "id": "assert-string",
        "request": {
            "entity": "user:alice",
            "relation": "memory:role",
            "value": {"type": "string", "v": "CEO"},
            "source": "agent:test",
            "confidence": 1.0,
            "scope": "company",
        },
        "expected_status": 201,
        "expected_value_type": "string",
    },
    {
        "id": "assert-text",
        "request": {
            "entity": "project:acme-roadmap",
            "relation": "roadmap:summary",
            "value": {"type": "text", "v": "Phase 0 complete; Phase 1 in flight."},
            "source": "agent:cto",
            "confidence": 0.9,
            "scope": "company",
        },
        "expected_status": 201,
        "expected_value_type": "text",
    },
    {
        "id": "assert-ref",
        "request": {
            "entity": "decision:use-sqlite",
            "relation": "rel:type",
            "value": {"type": "ref", "v": "stigmem://node.acme/decisions/use-sqlite"},
            "source": "agent:cto",
            "confidence": 1.0,
            "scope": "company",
        },
        "expected_status": 201,
        "expected_value_type": "ref",
    },
    {
        "id": "retract",
        "request": {
            "entity": "user:alice",
            "relation": "memory:role",
            "value": {"type": "string", "v": "retracted"},
            "source": "agent:test",
            "confidence": 0.0,
            "scope": "company",
        },
        "expected_status": 201,
        "expected_confidence": 0.0,
    },
]

QUERY_VECTORS = [
    {
        "id": "query-by-entity",
        "params": {"entity": "user:alice"},
        "expect_non_empty": True,
    },
    {
        "id": "query-by-entity-relation",
        "params": {"entity": "user:alice", "relation": "memory:role"},
        "expect_non_empty": True,
    },
    {
        "id": "query-min-confidence",
        "params": {"entity": "user:alice", "min_confidence": 0.8},
        "expect_fields": ["id", "entity", "relation", "value", "confidence"],
    },
    {
        "id": "query-include-contradicted",
        "params": {"include_contradicted": True},
        "expect_fields": ["id", "contradicted"],
    },
]

NODE_INFO_VECTOR = {
    "id": "node-info",
    "expected_fields": ["version", "node_id", "node_url", "auth", "federation"],
}
