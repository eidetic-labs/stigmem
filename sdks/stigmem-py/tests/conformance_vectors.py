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

# ---------------------------------------------------------------------------
# Lint vectors — spec §14 (v0.7)
#
# Each vector:
#   setup    — list of POST /v1/facts request bodies to assert before the lint sweep
#   request  — POST /v1/lint body (scope required; checks, entity, etc. optional)
#   expected — assertions about the 200 response
#     findings_min       — minimum number of findings expected (0 = clean)
#     findings_check     — all findings must have this check value (optional)
#     findings_severity  — at least one finding must have this severity (optional)
#     findings_empty     — True means findings must be [] (clean)
#
# Setup facts use a dedicated "lint-test" scope set unless noted; the test harness
# should create a fresh scope namespace per run to avoid cross-vector contamination.
# The entity "lint-test:scope-a" (company) and "lint-test:scope-b" (local) are used
# to verify scope isolation in lint-scope-filter.
# ---------------------------------------------------------------------------

LINT_VECTORS = [
    {
        "id": "lint-contradiction",
        "description": "Two live facts for same (entity, relation, scope) with different values",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/contradiction-target",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
            {
                "entity": "stigmem://node.test/lint-entity/contradiction-target",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CTO"},
                "source": "agent:test2",
                "confidence": 1.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["contradiction"],
            "entity": "stigmem://node.test/lint-entity/contradiction-target",
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "contradiction",
            "findings_severity": "error",
        },
    },
    {
        "id": "lint-stale",
        "description": "Fact with valid_until in the past (already expired)",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/stale-target",
                "relation": "memory:note",
                "value": {"type": "string", "v": "this fact is expired"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
                "valid_until": "2020-01-01T00:00:00Z",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["stale"],
            "entity": "stigmem://node.test/lint-entity/stale-target",
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "stale",
            "findings_severity": "warning",
        },
    },
    {
        "id": "lint-stale-lookahead",
        "description": "Fact within the lookahead window but not yet expired",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/lookahead-target",
                "relation": "memory:note",
                "value": {"type": "string", "v": "expiring soon"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
                # valid_until set at test time to now + 30 seconds;
                # use the harness helper set_valid_until_offset_s=30
                "valid_until": "__now_plus_30s__",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["stale"],
            "entity": "stigmem://node.test/lint-entity/lookahead-target",
            "stale_lookahead_s": 120,
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "stale",
            "findings_severity": "info",
        },
    },
    {
        "id": "lint-orphan",
        "description": "Entity where every fact has been retracted (confidence=0.0)",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/orphan-target",
                "relation": "memory:role",
                "value": {"type": "string", "v": "original"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
            # Retract the fact
            {
                "entity": "stigmem://node.test/lint-entity/orphan-target",
                "relation": "memory:role",
                "value": {"type": "string", "v": "original"},
                "source": "agent:test",
                "confidence": 0.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["orphan"],
            "entity": "stigmem://node.test/lint-entity/orphan-target",
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "orphan",
            "findings_severity": "info",
        },
    },
    {
        "id": "lint-broken-ref",
        "description": "Ref fact whose target entity has no live facts",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/ref-source",
                "relation": "roadmap:related",
                "value": {"type": "ref", "v": "stigmem://node.test/lint-entity/nonexistent-target"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["broken_ref"],
            "entity": "stigmem://node.test/lint-entity/ref-source",
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "broken_ref",
            "findings_severity": "warning",
        },
    },
    {
        "id": "lint-broken-ref-intent",
        "description": "Broken ref on intent:handoff_to — must be severity=error",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/handoff-orphan",
                "relation": "intent:handoff_to",
                "value": {"type": "ref", "v": "stigmem://node.test/agent/nonexistent-agent"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["broken_ref"],
            "entity": "stigmem://node.test/lint-entity/handoff-orphan",
        },
        "expected": {
            "findings_min": 1,
            "findings_check": "broken_ref",
            "findings_severity": "error",
        },
    },
    {
        "id": "lint-clean",
        "description": "Scope with a single healthy live fact — expects empty findings",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/clean-target",
                "relation": "memory:role",
                "value": {"type": "string", "v": "engineer"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "company",
            "checks": ["contradiction", "stale", "orphan", "broken_ref"],
            "entity": "stigmem://node.test/lint-entity/clean-target",
        },
        "expected": {
            "findings_empty": True,
        },
    },
    {
        "id": "lint-scope-filter",
        "description": "Contradiction in company scope is NOT visible when linting local scope",
        "setup": [
            {
                "entity": "stigmem://node.test/lint-entity/scope-isolated",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "agent:test",
                "confidence": 1.0,
                "scope": "company",
            },
            {
                "entity": "stigmem://node.test/lint-entity/scope-isolated",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CTO"},
                "source": "agent:test2",
                "confidence": 1.0,
                "scope": "company",
            },
        ],
        "request": {
            "scope": "local",
            "checks": ["contradiction"],
            "entity": "stigmem://node.test/lint-entity/scope-isolated",
        },
        "expected": {
            "findings_empty": True,
        },
    },
]
