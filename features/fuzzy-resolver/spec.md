# Fuzzy Resolver Spec

## Scope

Fuzzy resolver defines the node behavior for resolving a raw entity URI to the
best known canonical entity URI before a caller uses the result in fact queries
or write flows.

The feature covers:

- deterministic canonical normalization;
- explicit alias lookup through `entity_aliases`;
- same-type token-fuzzy candidate scoring over the live fact graph;
- authenticated entity-resolution and alias-management APIs.

The feature does not define phonetic matching, NLP entity linking, cross-type
resolution, or adapter-specific identity reconciliation.

## Resolution Pipeline

Resolution is ordered by confidence:

| Layer | Mechanism | Confidence |
| --- | --- | --- |
| 1 | Canonical normalization collapses case, whitespace, and hyphen/underscore variants. | Exact |
| 2 | `entity_aliases` maps explicit raw URI values to canonical URI values. | Authoritative |
| 3 | Token overlap, prefix matching, and sequence similarity rank same-type candidates. | Probabilistic |

The resolver stops after a layer 1 exact hit or a layer 2 alias hit. Layer 3
runs only when the canonical form is not an exact live-graph hit and no alias
exists.

## HTTP Surface

```http
GET /v1/entities/resolve?uri=<raw>&top_k=<int>&threshold=<float>
```

The caller must have read permission. The response includes the original query,
canonical value when normalization succeeds, best result, winning resolution
layer, alias hit if present, and ranked layer 3 candidates.

Alias management uses:

```http
POST /v1/aliases
GET /v1/aliases
DELETE /v1/aliases/{raw_uri}
```

Migration-managed aliases cannot be deleted through the user alias API.

## Layer 3 Scoring

Layer 3 searches only entities with the same informal type prefix, such as
`user:` or `agent:`. Formal `stigmem://` URIs and bare identifiers skip layer 3.

The score is the maximum of:

- exact token Jaccard overlap;
- prefix or initial match bonus;
- sequence similarity over concatenated id tokens.

The default threshold is `0.5`, and the API bounds `top_k` to 1 through 20.

## Canonical Spec Assignment

There is no Spec-X assignment for fuzzy resolver. The behavior is currently an
experimental core implementation detail with authenticated HTTP and storage
surfaces, not a standalone protocol module.
