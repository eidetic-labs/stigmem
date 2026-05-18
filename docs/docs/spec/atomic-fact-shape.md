---
title: Spec-01 Fact Model
sidebar_label: Spec-01 Fact Model
audience: Spec
description: "Spec-01-Fact-Model rendered entry point — fact tuple, value types, HLC, and fact-model boundaries."
---

# Spec-01-Fact-Model {#section-2}

**Status:** Rendered compatibility entry point for [`Spec-01-Fact-Model`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/01-fact-model.md).

The fact tuple, value types, scopes, HLC, identity, federation-trust fields.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

The maintained component spec is `Spec-01-Fact-Model`; legacy §2 anchors are retained for existing links.

<details>
<summary>Revisions before pre-reset draft: the pre-reset spec-draft, pre-reset draft, v1.0</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

Every piece of knowledge in Stigmem is an **atomic fact**:

```
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

| Field         | Type                              | Description |
|---------------|-----------------------------------|-------------|
| `entity`      | URI (see §2.5, §2.6)              | What this fact is about. Formal: `stigmem://company.example/user/alice`. Informal (deprecated): `user:alice`. Stored in canonical normalized form (§2.6). |
| `relation`    | string (namespaced predicate)     | What kind of statement this is. Examples: `memory:role`, `roadmap:status`, `preference:timezone`. |
| `value`       | `FactValue` (see §2.1)            | The asserted value. |
| `source`      | URI (see §2.5, §2.6)              | Who asserted the fact. Examples: `stigmem://company.example/agent/assistant`, `stigmem://company.example/user/alice`. Stored in canonical normalized form (§2.6). |
| `timestamp`   | ISO 8601 UTC datetime             | Wall-clock time when the fact was asserted. Set by the node at write time; clients may suggest. |
| `hlc`         | HLC string (see §2.4)            | Hybrid Logical Clock timestamp. Causality-preserving; required for federation. |
| `valid_until` | ISO 8601 UTC datetime or null     | Optional. If set, the fact is expired after this time. |
| `confidence`  | float in [0.0, 1.0]              | Asserting party's confidence. 1.0 = certain, 0.5 = uncertain, 0.0 = retracted. |
| `scope`       | `FactScope` (see §2.2)            | Visibility / federation boundary. |

A fact is **immutable once written**. Updates are new facts. The latest fact for
a given `(entity, relation, scope)` triple wins unless contradiction policy applies
(see §3.3).

**From `stigmem-spec-pre-reset draft.md`:**

*Stable sections §2.1–§2.6 unchanged from the pre-reset spec. The following fields are added to the fact record.*

**From `stigmem-spec-v1.0.md`:**

*Stable sections §2.1–§2.6 unchanged from the pre-reset spec. The following fields are added to the fact record.*

</details>

### §2.1 FactValue {#section-2-1}

A `FactValue` is a discriminated union that constrains what a fact can assert.
The `type` tag forces consumers to handle each variant explicitly — there is no
"any" escape hatch — so that queries, indexing, and synthesis can operate on
typed data without runtime introspection. The seven variants cover the practical
range of agent knowledge: short labels (`string`), longer prose (`text`),
numeric measurements, booleans, timestamps, inter-entity pointers (`ref`), and
an explicit "unknown" sentinel (`null`).

```
FactValue =
  | { type: "string",    v: string }          // short identifier or label (≤1 KB recommended)
  | { type: "text",      v: string }          // unbounded narrative; markdown allowed; ≤64 KB inline; use ref for larger
  | { type: "number",    v: number }
  | { type: "boolean",   v: boolean }
  | { type: "datetime",  v: ISO8601 }
  | { type: "ref",       v: URI }             // pointer to another entity or external content
  | { type: "null" }                          // explicit "unknown / not applicable"
```

The `string` vs `text` distinction exists because short labels (a role name, a
preference tag) have different indexing and display characteristics than
multi-paragraph narratives. Nodes index `string` values for exact-match
queries; `text` values feed the embedding pipeline (§20.2) for semantic recall.
The `ref` type creates typed edges in the knowledge graph — the recall pipeline
(§20.1) traverses `ref` values during k-hop expansion.

**`text` size guidance (v0.4):** Inline `text` values SHOULD be ≤ 64 KB. For larger payloads, assert a `ref` fact pointing to external storage and keep the text value as a summary. Nodes MAY reject `text` values above their configured limit; they MUST return HTTP 413 if they do.

### §2.2 FactScope {#section-2-2}

Scope is the visibility fence that determines which facts leave a node during
federation. It is a single string enum — not a complex policy document —
because the common case is simple ("this stays here" vs "this can be shared")
and complex cross-scope propagation rules (§6.4) build on top of this
primitive. The four levels form a strict hierarchy from most private to most
shareable:

```
FactScope =
  | "local"     // visible only within this node, never federated
  | "team"      // visible within a logical team boundary (node-defined)
  | "company"   // visible within the owning company node
  | "public"    // federatable to any peer that has a handshake with this node
```

Nodes MUST NOT federate `local` or `team` facts without explicit operator override.
`company`-scoped facts are only federated when the active PeerDeclaration explicitly
includes `"company"` in `allowed_scopes` (see §6.1).

### §2.3 Reification (N-ary Relationships) {#section-2-3}

The fact tuple is binary — one entity, one relation, one value — but real-world
knowledge often involves three or more parties (e.g. "Company A approved
Company B's policy via board vote"). Reification handles this by minting a
synthetic entity that *represents the relationship itself*, then attaching the
participants as facts about that entity. This pattern avoids adding an
`object` column to the fact table (which would complicate queries and indexing
for the overwhelmingly binary common case) while still supporting complex
relationships when they arise.

To create an N-ary relationship, mint a synthetic entity `stigmem:rel:{uuid}`
and assert facts about it:

```
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"stigmem://company.example/company/a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"stigmem://company.example/company/b"})
(entity="stigmem:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
```

`rel:subject`, `rel:object`, and `rel:type` are reserved in the `rel:` namespace (see §9). The graph traversal engine (§20.1) follows `ref` values out of reified entities the same way it follows any other `ref`, so reified relationships participate naturally in k-hop recall.

### §2.4 Hybrid Logical Clock (HLC) — pre-reset {#section-2-4}

Wall-clock timestamps alone cannot establish causality in a distributed system
because clocks drift. A pure logical clock (Lamport-style) preserves causality
but loses correlation with real time. Stigmem uses a **Hybrid Logical Clock**
that combines both: the `wall_ms` component anchors events to real time (for
human debugging and time-travel queries — §24), while the `counter` component
preserves causality even when two events share the same millisecond.

Every node maintains a single HLC value:

```
HLC = wall_ms || counter
```

Format: `"{wall_ms_utc}.{counter}"` — e.g. `"1746230400000.003"`.

The string encoding uses a dot separator so that lexicographic string comparison
produces correct causal ordering without parsing. The `wall_ms` component is
zero-padded to 13 digits (sufficient until year 2286); the `counter` component
is zero-padded to 3 digits per node (overflow creates a new millisecond bucket).

**Advance rules:**
1. On local write: `hlc = max(now_ms, last_hlc_ms)` as `wall_ms`; increment `counter` if `wall_ms` unchanged.
2. On receiving a federated fact: `hlc = max(now_ms, received_hlc_ms)` as `wall_ms`; increment counter.

**Causal ordering:** Two facts `a`, `b` are causally ordered iff `a.hlc < b.hlc`. Equal HLCs on different nodes indicate concurrent writes; standard contradiction policy (§3.3) applies.

**Wire encoding:** `hlc` is included in all fact responses and replication payloads. Clients that do not understand HLC MAY ignore the field; nodes MUST store and propagate it.

### §2.5 Entity URI Scheme — pre-reset Normative {#section-2-5}

**pre-reset open question §8.1 resolved.** The entity URI scheme is now normative.

#### Formal URI scheme

```
stigmem://{authority}/{type}/{id}
```

| Component   | Description | Examples |
|-------------|-------------|---------|
| `authority` | Hostname of the Stigmem node that owns this entity namespace | `company.example`, `node.example.com` |
| `type`      | Entity type slug (lowercase, no spaces) | `user`, `agent`, `project`, `issue`, `decision`, `team` |
| `id`        | Opaque stable identifier for the entity | `alice`, `cto`, `acme-roadmap`, `EG-42` |

**Examples:**
- `stigmem://company.example/user/alice`
- `stigmem://company.example/agent/cto`
- `stigmem://company.example/issue/EG-42`
- `stigmem://node.acme/decision/use-sqlite`

#### Deprecation of informal URIs

Informal URIs (colon-separated shorthand such as `user:alice`, `agent:cto`,
`project:acme-roadmap`) are **deprecated as of pre-reset**.

**Node behavior:**
- Nodes MUST accept informal URIs without rejecting them (backward compatibility).
- Nodes MUST emit a deprecation warning to stderr when storing a fact whose `entity`
  or `source` field does not match the `stigmem://` scheme.
- The deprecation warning MUST include the offending URI and SHOULD include a migration
  hint pointing to the formal scheme.
- Nodes MUST NOT auto-rewrite informal URIs to formal URIs on ingest (that would
  silently alter provenance).

**Adapter behavior:**
- Adapters SHOULD use formal URIs for all new fact assertions as of pre-reset.
- Adapters MUST NOT emit informal URIs in new code targeting pre-reset or later.
- Existing stored facts with informal URIs remain valid through at least the pre-reset spec.

**Collision rationale:** Informal URIs are inherently ambiguous once federation
is active. `user:alice` on node A and `user:alice` on node B may refer to different
people. The formal scheme binds the authority to the URI, preventing silent identity
collisions across federated nodes.

**pre-reset note:** All components of the formal URI are normalized to lowercase on ingest (§2.6). `stigmem://company.example/issue/EG-42` is stored as `stigmem://company.example/issue/eg-42`.

### §2.6 Entity Naming Rules — pre-reset Normative {#section-2-6}

This section defines canonical entity naming rules and the **strict normalizer** contract. The goal is to prevent **silent entity fragmentation**: multiple facts about the same real-world entity using different URI representations that create disconnected entity nodes in the store.

**pre-reset scope:** The strict normalizer addresses case-based and whitespace-based fragmentation deterministically. Full alias resolution (e.g. `user:alice` ≡ `user:a.smith`) is deferred to the pre-reset design-partner window fuzzy resolver.

#### §2.6.1 The fragmentation problem {#section-2-6-1}

Before strict normalization, the following assertions create separate entities for the same project:

```
entity="project/eg-18"                            (informal, slash separator, lowercase)
entity="project/EG-18"                            (informal, slash separator, uppercase)
entity="stigmem://company.example/project/eg-18"     (formal, lowercase id)
entity="stigmem://company.example/project/EG-18"     (formal, uppercase id)
```

All four refer to the same project. Without normalization, queries for any one form miss the others entirely, and contradiction detection never fires for facts that should conflict.

#### §2.6.2 Canonical form {#section-2-6-2}

The canonical form of an entity URI after normalization is the lowercase form of that URI with surrounding whitespace trimmed and internal whitespace in the `id` component collapsed to hyphens.

For **formal URIs** (`stigmem://authority/type/id`):

| Component   | Canonical rule |
|-------------|---------------|
| `authority` | Lowercase; trim surrounding whitespace |
| `type`      | Lowercase; trim surrounding whitespace |
| `id`        | Lowercase; trim surrounding whitespace; collapse internal whitespace runs to a single hyphen |

For **informal URIs** (any non-`stigmem://` form):
- Lowercase the entire string; trim surrounding whitespace; collapse internal whitespace to hyphens.
- The URI format is **preserved** (informal stays informal — not converted to formal).
- The §2.5 constraint "nodes MUST NOT auto-rewrite informal URIs to formal URIs" is honored: lowercasing the informal form is not the same as expanding it to the formal scheme.

#### §2.6.3 Strict normalizer — normative algorithm {#section-2-6-3}

Reference implementation at `stigmem/node/src/stigmem_node/entity_normalizer.py`:

```python
import re

_FORMAL_URI_RE = re.compile(r"^stigmem://([^/]+)/([^/]+)/(.+)$")
_WHITESPACE_RE = re.compile(r"\s+")

class NormalizationError(ValueError):
    pass

def normalize_entity_uri(raw: str) -> str:
    """Return the canonical form of an entity URI string.

    Raises NormalizationError on empty or whitespace-only input.
    """
    if not raw or not raw.strip():
        raise NormalizationError("entity URI must not be empty")

    stripped = raw.strip()
    m = _FORMAL_URI_RE.match(stripped)
    if m:
        authority = m.group(1).strip().lower()
        type_slug = m.group(2).strip().lower()
        id_part   = _WHITESPACE_RE.sub("-", m.group(3).strip().lower())
        if not authority or not type_slug or not id_part:
            raise NormalizationError(
                f"normalization produced empty component in formal URI: {raw!r}"
            )
        return f"stigmem://{authority}/{type_slug}/{id_part}"

    # Informal URI: lowercase and collapse whitespace; format preserved
    return _WHITESPACE_RE.sub("-", stripped.lower())
```

**Invariants the normalizer MUST satisfy:**

1. **Deterministic:** identical inputs always produce identical outputs.
2. **Idempotent:** `normalize(normalize(x)) == normalize(x)` for all valid inputs.
3. **Total on valid inputs:** every non-empty string produces exactly one output; invalid inputs raise `NormalizationError`.

**What the strict normalizer does NOT do:**
- Alias resolution (e.g., `user:alice` ≡ `user:a.smith`) — the pre-reset design-partner window fuzzy resolver.
- Existence validation against the fact store.
- Semantic similarity matching.
- Conversion of informal URIs to formal URIs (§2.5 prohibits silent auto-rewrite).

#### §2.6.4 Ingest-path contract {#section-2-6-4}

Nodes MUST apply the strict normalizer to the `entity` and `source` fields of every incoming fact **before** persistence:

1. If `normalize_entity_uri` returns a canonical URI, store the canonical form.
2. If the input was an informal URI (does not match `stigmem://`), also emit a deprecation warning to stderr as specified in §2.5.
3. If `normalize_entity_uri` raises `NormalizationError`, reject the fact:

```
HTTP 400
{ "error": "invalid_entity_uri", "detail": "<NormalizationError message>" }
```

**Why normalize at ingest (not query):** Query-time normalization would require every consumer to carry normalization logic and would leave non-canonical data permanently in the store. Ingest normalization ensures the stored form is always canonical; all queries use exact string matching on the canonical form, keeping query performance O(1) on indexed lookups.

**Retraction and contradiction compatibility:** Ingest normalization is safe for retractions (§5.4) and contradiction detection (§3.3). If a retraction and the original fact both normalize to the same canonical entity, they match correctly. A client sending a retraction for a non-canonical URI normalizes to the same canonical form as the original, and retraction semantics apply as expected.

#### §2.6.5 Query-time backward compatibility {#section-2-6-5}

For nodes upgrading to pre-reset, **query parameters are also normalized** before matching:

```
GET /v1/facts?entity=<raw>&...
```

The node MUST apply `normalize_entity_uri` to the `entity` and `source` query parameters before executing the database query. This allows clients holding references to pre-normalization forms to still retrieve existing facts written after pre-reset is deployed.

For pre-pre-reset facts stored with non-canonical URIs, the alias table (§2.6.6, migration 003) is the recommended migration path.

#### §2.6.6 Migration guide for existing facts {#section-2-6-6}

Facts stored before pre-reset strict normalization was deployed may use informal URIs or non-canonical formal URIs. Because facts are immutable (§2), they cannot be rewritten in place. The following migration strategies are available:

**Option A — Alias table (recommended for production nodes)**

Migration 003 adds an `entity_aliases` table that maps known informal/legacy URIs to their canonical equivalents (see §10). Populate it by scanning the `facts` table for non-canonical `entity` and `source` values and inserting the raw → canonical mapping. At query time, the node can join against this table to find pre-pre-reset facts via canonical queries.

**Option B — Re-assertion sweep (for smaller nodes or clean migration windows)**

For each fact with a non-canonical entity URI:
1. Assert a new fact with the canonical entity, the same `(relation, value, scope, confidence)`, and provenance `source="system:stigmem:migration"`.
2. Retract the original fact by asserting `confidence=0.0` for the original `(entity_raw, relation, scope)`.

The original facts are retained in the store with `confidence=0.0` for audit purposes.

**Phased rollout recommendation:**

| Phase | Action |
|-------|--------|
| pre-reset deploy | Enable strict normalizer on ingest. Query normalization enabled. |
| +2 weeks | Scan facts table; populate alias table for any non-canonical existing facts. |
| +4 weeks | Run re-assertion sweep for nodes with < 10k facts; otherwise maintain alias table. |
| the pre-reset spec target | Remove alias table read path; all facts use canonical URIs. |

---

### §2.7 Garden Field {#section-2-7}

An optional `garden_id` field on a fact associates it with a Memory Garden (§17).

```
FactRecord (the pre-reset spec extension):
  ...all the pre-reset spec fields...
  garden_id: URI | null    // stigmem://authority/garden/{slug}; null = no garden
  attested:  boolean | null  // source attestation result (§18); null = not applicable
```

**`garden_id` invariant:** When `garden_id` is set:
1. The garden MUST exist on the local node.
2. The writing principal MUST hold `writer` or `admin` role in the garden.
3. The fact's `scope` MUST equal the garden's declared `scope`.
4. Garden-tagged facts are subject to garden ACL at read time (§17.3).

**`garden_id` on federation:** Garden membership is node-local. Facts with `garden_id` set MUST NOT be replicated to peers. Nodes MUST silently drop `garden_id` from federated facts they receive (so cross-node garden membership doesn't accidentally leak or create ghost associations).

**`attested` semantics:**

| Value  | Meaning |
|--------|---------|
| `true`  | Node verified that `source` equals the caller's authenticated `entity_uri`. |
| `false` | Source/identity mismatch detected; fact accepted in `warn` or `off` mode. |
| `null`  | Attestation not applicable: auth disabled, federation ingest, or system fact. |

---

<details>
<summary>Revisions before v1.0: pre-reset draft</summary>

**From `stigmem-spec-pre-reset draft.md`:**

### 2.7 Garden Field — the pre-reset spec

An optional `garden_id` field on a fact associates it with a Memory Garden (§17).

```
FactRecord (the pre-reset spec extension):
  ...all the pre-reset spec fields...
  garden_id: URI | null    // the pre-reset spec: stigmem://authority/garden/{slug}; null = no garden
  attested:  boolean | null  // the pre-reset spec: source attestation result (§18); null = not applicable
```

**`garden_id` invariant:** When `garden_id` is set:
1. The garden MUST exist on the local node.
2. The writing principal MUST hold `writer` or `admin` role in the garden.
3. The fact's `scope` MUST equal the garden's declared `scope`.
4. Garden-tagged facts are subject to garden ACL at read time (§17.3).

**`garden_id` on federation:** Garden membership is node-local. Facts with `garden_id` set MUST NOT be replicated to peers. Nodes MUST silently drop `garden_id` from federated facts they receive (so cross-node garden membership doesn't accidentally leak or create ghost associations).

**`attested` semantics:**

| Value  | Meaning |
|--------|---------|
| `true`  | Node verified that `source` equals the caller's authenticated `entity_uri`. |
| `false` | Source/identity mismatch detected; fact accepted in `warn` or `off` mode. |
| `null`  | Attestation not applicable: auth disabled, federation ingest, or system fact. |

---

</details>

### §2.8 Federation Trust Fields {#section-2-8}

Three optional fields extend the fact record to carry provenance, attestation evidence, and source-trust information:

```
FactRecord (v0.9.0a1):
  ...all canonical FactRecord fields...
  derived_from:      [FactHash]  | null  // provenance: hashes of facts this derives from (§19.6)
  attestation_chain: [Signature] | null  // ordered attestation signatures (§19.6)
  source_trust:      float | null        // cached source-trust score at write time (§19.4); null = not computed
```

Where:
- `FactHash` is a hex-encoded SHA-256 hash of a normalized fact record (see §19.6.2).
- `Signature` is a base64url-encoded Ed25519 signature from an org manifest key (§19.1).
- `source_trust` is a float in [0.0, 1.0]. Nodes SHOULD populate this at write time when source-trust computation is enabled (§19.4). Nodes MUST NOT reject facts with a low `source_trust` at write time; the value is informational.

**Invariants:**
1. `derived_from` is ordered by logical derivation; the first entry is the most direct antecedent.
2. `attestation_chain` is ordered from innermost to outermost signer; an empty array is semantically equivalent to `null`.
3. `source_trust` is recomputed at recall time and MUST NOT be relied upon as final from the stored record; the stored value is a snapshot useful for audit.

---
