---
id: fuzzy-entity-resolver
title: Fuzzy Entity Resolver
sidebar_label: Fuzzy Entity Resolver
audience: Integrator
---

# Fuzzy Entity Resolver

**Audience:** Agent developers and node operators who need to match variant entity URIs (abbreviated names, legacy aliases, typos) to a canonical entity in the fact store.

Spec §2.6.6 (v0.8). Implemented in Track F.

Human-authored facts routinely produce variant URIs for the same real-world entity — `user:alice`, `user:a.smith`, `user:alice-smith` — because the canonical normalizer collapses whitespace and case but cannot infer that two different id segments refer to the same person. The fuzzy entity resolver bridges this gap.

---

## Three-layer resolution pipeline

Resolution is ordered by confidence:

| Layer | Mechanism | Speed | Confidence |
|-------|-----------|-------|-----------|
| **1 — Canonical normalisation** | `entity_normalizer.py` collapses case, whitespace, hyphen/underscore variants | Instant | Exact |
| **2 — Alias table** | Explicit `user:alice → user:a.smith` mappings in `entity_aliases` | Fast (indexed) | Authoritative |
| **3 — Token-fuzzy scoring** | Token overlap + prefix match + SequenceMatcher over live fact graph | Milliseconds | Probabilistic |

The resolver stops as soon as it finds a Layer 1 or Layer 2 match and returns that result without running further layers.

---

## GET /v1/entities/resolve

Resolve a raw entity URI against the three layers.

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `uri` | string | required | Raw entity URI to resolve |
| `top_k` | int | 5 | Max Layer 3 fuzzy candidates (1–20) |
| `threshold` | float | 0.5 | Minimum fuzzy score for Layer 3 candidates (0.0–1.0) |

**Response (200 OK):**

```json
{
  "query": "user:alice",
  "canonical": "user:alice",
  "best": "user:a.smith",
  "resolution_layer": 2,
  "layer1_match": false,
  "layer2_match": "user:a.smith",
  "layer3_candidates": []
}
```

- **`best`** — the highest-confidence resolved URI. Use this for subsequent fact queries.
- **`resolution_layer`** — which layer produced the result (1, 2, 3, or `null` if unresolved).
- **`layer3_candidates`** — ranked list of fuzzy matches when Layer 3 runs:

```json
{
  "query": "user:a.s",
  "canonical": "user:a.s",
  "best": "user:a.smith",
  "resolution_layer": 3,
  "layer1_match": false,
  "layer2_match": null,
  "layer3_candidates": [
    {
      "uri": "user:a.smith",
      "score": 0.8333,
      "match_note": "token_score=0.83 ('a.s' ~ 'a.smith')"
    },
    {
      "uri": "user:alice",
      "score": 0.5,
      "match_note": "token_score=0.50 ('a.s' ~ 'alice')"
    }
  ]
}
```

**`curl` examples:**

```bash
# Resolve by abbreviated name
curl -s "http://localhost:8000/v1/entities/resolve?uri=user:alice" \
  -H 'Authorization: Bearer stgm_...' | jq '{best, resolution_layer}'

# Stricter threshold — only high-confidence fuzzy matches
curl -s "http://localhost:8000/v1/entities/resolve?uri=user:a.s&threshold=0.7" \
  -H 'Authorization: Bearer stgm_...' | jq .

# Broader search — more candidates
curl -s "http://localhost:8000/v1/entities/resolve?uri=user:alice&top_k=10" \
  -H 'Authorization: Bearer stgm_...' | jq '.layer3_candidates[]'
```

---

## Managing explicit aliases (Layer 2)

Use the `/v1/aliases` endpoints to register permanent mappings for known legacy URIs or renamed entities.

### POST /v1/aliases — register an alias

```bash
curl -s -X POST http://localhost:8000/v1/aliases \
  -H 'Authorization: Bearer stgm_...' \
  -H 'Content-Type: application/json' \
  -d '{
    "raw_uri": "user:alice",
    "canonical_uri": "user:alice-smith"
  }' | jq .
# → {"raw_uri": "user:alice", "canonical_uri": "user:alice-smith", "kind": "user", "created_at": "..."}
```

Alias `kind` is `"user"` for API-registered aliases. Migration tool-managed aliases have kind `"migration"` and cannot be deleted via the API.

### GET /v1/aliases — list aliases

```bash
# All aliases
curl -H 'Authorization: Bearer stgm_...' http://localhost:8000/v1/aliases | jq .

# Aliases that resolve to a specific canonical URI
curl -H 'Authorization: Bearer stgm_...' \
  "http://localhost:8000/v1/aliases?canonical_uri=user:alice-smith" | jq .
```

### DELETE /v1/aliases/\{raw\_uri\} — remove an alias

```bash
curl -s -X DELETE \
  -H 'Authorization: Bearer stgm_...' \
  "http://localhost:8000/v1/aliases/user:alice"
# → 204 No Content
```

URL-encode the raw_uri if it contains special characters.

---

## How Layer 3 scoring works

Layer 3 runs only when Layers 1 and 2 find nothing. It fetches all entities with the same type prefix (e.g. `user:*`) from the live fact graph and scores them using a combined metric:

- **Jaccard** — exact token overlap (split on `.`, `-`, `_`, `/`, whitespace)
- **Prefix bonus** — one token in the query is a prefix of a token in the candidate
- **SequenceMatcher ratio** — character-sequence similarity on the concatenated id segments

The score is `max(jaccard, prefix_bonus, seq_ratio)`, clamped to `[0, 1]`. Default threshold is `0.5`.

**Example:** `user:alice` vs `user:a.smith`
- Query tokens: `["alice"]` → Candidate tokens: `["a", "smith"]`
- Prefix bonus: `"alice"[0]` = `"a"`, candidate has token `"a"` → `+0.3`; `"alice"[:2]` = `"al"` does not match `"a.smith"` tokens
- SequenceMatcher: `"alice"` vs `"asmith"` → ~0.5
- Score: `max(0.0, 0.3, 0.5)` = **0.5** (at threshold)

Increase `threshold` to reduce false positives; decrease it for broader matching of unusual URI formats.

---

## Using resolved URIs in fact queries

After resolving, use `best` as the entity in `GET /v1/facts`:

```bash
BEST_URI=$(curl -s "http://localhost:8000/v1/entities/resolve?uri=user:alice" \
  -H 'Authorization: Bearer stgm_...' | jq -r .best)

curl -s "http://localhost:8000/v1/facts?entity=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$BEST_URI'))")" \
  -H 'Authorization: Bearer stgm_...' | jq '.facts[] | {entity, relation, value}'
```

---

## Limitations

- **Type-prefix scoped:** Layer 3 only searches entities with the same type prefix (`user:`, `agent:`, etc.). Cross-type resolution is not supported.
- **Formal URIs excluded from Layer 3:** `stigmem://` URIs bypass Layer 3 (use Layer 1 normalisation only).
- **No phonetic / NLP matching yet:** The full Kompl-style resolver (phonetic matching, NLP-based entity linking) is deferred to Phase 7. Layer 3 covers the common case of abbreviated names and initials.

---

## See also

- [Asserting Facts](./asserting-facts) — `entity` field and canonical URI format
- [Querying Facts](./querying-facts) — using `entity` filters with exact URIs
- Spec §2.6.6 — Fuzzy entity resolution
