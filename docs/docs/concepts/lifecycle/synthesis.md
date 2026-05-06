---
title: Synthesis
sidebar_label: Synthesis
audience: Integrator
---

# Synthesis

:::caution Experimental
`POST /v1/synthesis` and `synthesize_scope` MCP tool are **draft** in spec v0.8 (§16). The API shape is stable for testing; will be promoted to normative in v0.9.
:::

**Audience:** Agent developers who need a clean, contradiction-aware snapshot of current knowledge in a scope — particularly useful for injecting context at agent boot time.

## Overview

The stigmem facts table is append-only: queries against it can return multiple conflicting values for the same `(entity, relation)` pair, one per assertion. Synthesis collapses that history into a single **best-current-value** per `(entity, relation, scope)` triple using confidence-weighted resolution:

- If there is one live fact for a pair, it is returned directly.
- If there are conflicting live facts, the higher-confidence value wins (equal confidence → higher HLC wins, per §3.3).
- Contradictions are surfaced explicitly via `contradicted: true` rather than silently hidden — the caller sees both the winning value and the losing alternative.

Synthesis is read-only. It writes nothing to the facts table.

## Quick example

```bash
# Get current state of the "company" scope
curl -X POST $STIGMEM_URL/v1/synthesis \
  -H "Authorization: Bearer $STIGMEM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"scope": "company", "min_confidence": 0.5}'
```

```json
{
  "synthesized_at": "2026-05-02T18:05:00Z",
  "scope": "company",
  "fact_count": 3210,
  "contradiction_count": 2,
  "filtered_count": 48,
  "summary": [
    {
      "entity": "user:alice",
      "relation": "memory:preferred_language",
      "scope": "company",
      "value": "Python",
      "confidence": 0.95,
      "hlc": "1746204300000-0001-node1",
      "contradicted": false
    },
    {
      "entity": "project:api-rewrite",
      "relation": "project:status",
      "scope": "company",
      "value": "in_progress",
      "confidence": 0.8,
      "hlc": "1746204100000-0003-node2",
      "contradicted": true,
      "alt_value": "planning",
      "alt_confidence": 0.75
    }
  ]
}
```

The second entry shows a contradiction: two agents disagree on `project:api-rewrite / project:status`. `value` is the winner (`in_progress`, confidence 0.8); `alt_value` is the loser. Use `POST /v1/conflicts/:id/resolve` to adjudicate.

## Use case: agent context injection

A common pattern is to call `synthesize_scope` at agent boot to hydrate the agent's working memory:

```python
import httpx

async def get_context(scope: str, min_confidence: float = 0.6) -> list[dict]:
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"{STIGMEM_URL}/v1/synthesis",
            headers={"Authorization": f"Bearer {STIGMEM_API_KEY}"},
            json={"scope": scope, "min_confidence": min_confidence},
        )
        r.raise_for_status()
        data = r.json()
        if data["contradiction_count"] > 0:
            # Surface contradictions in the agent's reasoning context
            contradicted = [e for e in data["summary"] if e["contradicted"]]
            # log or handle contradicted entries
        return data["summary"]
```

This gives the agent a clean view of reliable current state without needing to manage contradiction filtering itself.

## API reference

```
POST /v1/synthesis
Authorization: Bearer <api-key>
Content-Type: application/json
```

**Request body:**

| Field | Type | Required | Description |
|---|---|---|---|
| `scope` | FactScope | yes | Scope to synthesize (`local`, `team`, `company`, `public`) |
| `entity` | URI string | no | Restrict to facts about a single entity |
| `min_confidence` | float [0.0–1.0] | no | Exclude entries below this confidence threshold (default `0.0`) |
| `include_expired` | boolean | no | Include expired facts (`valid_until < now`); default `false` |

**Response (200 OK):**

| Field | Description |
|---|---|
| `summary` | Array of `SynthesisEntry` objects (see below) |
| `synthesized_at` | ISO 8601 UTC timestamp |
| `scope` | Scope that was synthesized |
| `fact_count` | Total live facts evaluated |
| `contradiction_count` | Number of entries with `contradicted: true` |
| `filtered_count` | Entries excluded by `min_confidence` |

**`SynthesisEntry` shape (§16.1):**

| Field | Type | Description |
|---|---|---|
| `entity` | URI | Entity subject |
| `relation` | string | Relation URI |
| `scope` | FactScope | Fact scope |
| `value` | FactValue | Winning fact value |
| `confidence` | float | Winning fact confidence |
| `hlc` | string | Hybrid Logical Clock of the winning fact |
| `contradicted` | boolean | `true` if an unresolved contradiction exists |
| `alt_value` | FactValue? | Losing fact value (only when `contradicted: true`) |
| `alt_confidence` | float? | Losing fact confidence (only when `contradicted: true`) |

**Authorization:** API key must have **read access** to the requested scope.

### Error responses

| HTTP | Condition |
|---|---|
| 400 | Missing/invalid `scope`; `min_confidence` outside `[0.0, 1.0]` |
| 403 | API key lacks read access to the scope |

## MCP tool: `synthesize_scope`

```python
# Via MCP — restrict to a single entity
result = await mcp.call_tool("synthesize_scope", {
    "scope": "team",
    "entity": "project:api-rewrite",
    "min_confidence": 0.5
})
```

## The lint → decay → synthesis pipeline (§16.5)

The three Phase 6 operational tools answer different questions:

| Tool | Question | Writes? |
|---|---|---|
| `lint_scope` | "What is wrong?" | No |
| `decay_scope` | "Apply configured remediation" | Yes |
| `synthesize_scope` | "What do I currently know?" | No |

**Typical workflow:**

1. **Boot** — call `synthesize_scope` for reliable context injection.
2. **Background (periodic)** — call `lint_scope` to surface health issues; call `decay_scope` to apply configured policies.
3. **Resolution** — call `POST /v1/conflicts/:id/resolve` for contradictions that synthesis surfaces.

## Synthesis vs. `GET /v1/facts`

| | `GET /v1/facts` | `POST /v1/synthesis` |
|---|---|---|
| Returns | Raw fact rows (all versions) | One best-value per `(entity, relation)` |
| Contradictions | All conflicting facts returned | Winner shown; loser in `alt_value` |
| Use case | Audit, replication, debugging | Agent context injection, current-state queries |
| Filtering | Cursor-paginated, filter by entity/relation | `min_confidence`, `include_expired` |

## See also

- [Decay guide](/docs/build/guides/decay) — apply configured decay policies before synthesizing for the cleanest view
- [Conflict resolution guide](/docs/build/guides/conflict-resolution) — resolve the contradictions synthesis surfaces
- Spec §16 — Synthesis (authoritative algorithm and wire format)
- Spec §3.3 — Contradiction resolution order
