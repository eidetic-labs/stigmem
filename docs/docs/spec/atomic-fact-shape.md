---
title: Spec-01 Fact Model
sidebar_label: Spec-01 Fact Model
audience: Spec
description: "Spec-01-Fact-Model rendered entry point — fact tuple, value types, HLC, and fact-model boundaries."
---

# Spec-01-Fact-Model \{#section-2\}

<p className="stigmem-meta"><span>9 min read</span><span>Spec contributor · SDK author</span><span>Fact tuple foundations</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-01-Fact-Model`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/01-fact-model.md).
The fact tuple, value types, scopes, HLC, identity, federation-trust
fields.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
The maintained component spec is `Spec-01-Fact-Model`; legacy §2
anchors are retained for existing links.
:::

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

### §2.1 FactValue \{#section-2-1\}

A `FactValue` is a discriminated union that constrains what a fact
can assert. The `type` tag forces consumers to handle each variant
explicitly — there is no "any" escape hatch — so that queries,
indexing, and synthesis can operate on typed data without runtime
introspection.

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

<div className="stigmem-keypoint">

**The `string` vs `text` distinction exists because short labels and multi-paragraph narratives have different indexing characteristics.**

Nodes index <code>string</code> values for exact-match queries;
<code>text</code> values feed the embedding pipeline (§20.2) for
semantic recall. The <code>ref</code> type creates typed edges in
the knowledge graph — the recall pipeline (§20.1) traverses
<code>ref</code> values during k-hop expansion.

</div>

**`text` size guidance (v0.4):** Inline `text` values SHOULD be ≤ 64
KB. For larger payloads, assert a `ref` fact pointing to external
storage and keep the text value as a summary. Nodes MAY reject
`text` values above their configured limit; they MUST return HTTP
413 if they do.

### §2.2 FactScope \{#section-2-2\}

Scope is the visibility fence that determines which facts leave a
node during federation. The four levels form a strict hierarchy
from most private to most shareable.

```
FactScope =
  | "local"     // visible only within this node, never federated
  | "team"      // visible within a logical team boundary (node-defined)
  | "company"   // visible within the owning company node
  | "public"    // federatable to any peer that has a handshake with this node
```

Nodes MUST NOT federate `local` or `team` facts without explicit
operator override. `company`-scoped facts are only federated when
the active PeerDeclaration explicitly includes `"company"` in
`allowed_scopes` (see §6.1).

### §2.3 Reification (N-ary relationships) \{#section-2-3\}

The fact tuple is binary — one entity, one relation, one value —
but real-world knowledge often involves three or more parties.
Reification handles this by minting a synthetic entity that
*represents the relationship itself*, then attaching the
participants as facts about that entity.

```
(entity="stigmem:rel:abc123", relation="rel:subject",  value={type:"ref", v:"stigmem://company.example/company/a"})
(entity="stigmem:rel:abc123", relation="rel:object",   value={type:"ref", v:"stigmem://company.example/company/b"})
(entity="stigmem:rel:abc123", relation="rel:type",     value={type:"string", v:"policy:board-approval"})
```

`rel:subject`, `rel:object`, and `rel:type` are reserved in the
`rel:` namespace (see §9). The graph traversal engine (§20.1)
follows `ref` values out of reified entities the same way it
follows any other `ref`, so reified relationships participate
naturally in k-hop recall.

### §2.4 Hybrid Logical Clock (HLC) — pre-reset \{#section-2-4\}

Wall-clock timestamps alone cannot establish causality in a
distributed system because clocks drift. A pure logical clock
(Lamport-style) preserves causality but loses correlation with real
time. Stigmem uses a **Hybrid Logical Clock** that combines both.

Every node maintains a single HLC value:

```
HLC = wall_ms || counter
```

Format: `"{wall_ms_utc}.{counter}"` — e.g. `"1746230400000.003"`.

The string encoding uses a dot separator so that lexicographic
string comparison produces correct causal ordering without parsing.
The `wall_ms` component is zero-padded to 13 digits (sufficient
until year 2286); the `counter` component is zero-padded to 3 digits
per node (overflow creates a new millisecond bucket).

**Advance rules:**

<div className="stigmem-fields">

<div>
<dt>Trigger</dt>
<dt><span className="stigmem-fields__type"><code>wall_ms</code> rule</span></dt>
<dd>Counter rule</dd>
</div>

<div>
<dt>Local write</dt>
<dt><span className="stigmem-fields__type"><code>max(now_ms, last_hlc_ms)</code></span></dt>
<dd>Increment if <code>wall_ms</code> unchanged.</dd>
</div>

<div>
<dt>Receiving federated fact</dt>
<dt><span className="stigmem-fields__type"><code>max(now_ms, received_hlc_ms)</code></span></dt>
<dd>Increment counter.</dd>
</div>

</div>

**Causal ordering:** Two facts `a`, `b` are causally ordered iff
`a.hlc < b.hlc`. Equal HLCs on different nodes indicate concurrent
writes; standard contradiction policy (§3.3) applies.

**Wire encoding:** `hlc` is included in all fact responses and
replication payloads. Clients that do not understand HLC MAY ignore
the field; nodes MUST store and propagate it.

### §2.5 Entity URI scheme — pre-reset normative \{#section-2-5\}

<div className="stigmem-keypoint">

**pre-reset open question §8.1 resolved.**

The entity URI scheme is now normative.

</div>

#### Formal URI scheme

```
stigmem://{authority}/{type}/{id}
```

<div className="stigmem-fields">

<div>
<dt>Component</dt>
<dt><span className="stigmem-fields__type">Examples</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>authority</code></dt>
<dt><span className="stigmem-fields__type"><code>company.example</code></span></dt>
<dd>Hostname of the Stigmem node that owns this entity namespace.</dd>
</div>

<div>
<dt><code>type</code></dt>
<dt><span className="stigmem-fields__type"><code>user</code>, <code>agent</code>, <code>project</code>, <code>issue</code></span></dt>
<dd>Entity type slug (lowercase, no spaces).</dd>
</div>

<div>
<dt><code>id</code></dt>
<dt><span className="stigmem-fields__type"><code>alice</code>, <code>cto</code>, <code>EG-42</code></span></dt>
<dd>Opaque stable identifier for the entity.</dd>
</div>

</div>

**Examples:**

<div className="stigmem-grid">

<div><h4><code>stigmem://company.example/user/alice</code></h4></div>
<div><h4><code>stigmem://company.example/agent/cto</code></h4></div>
<div><h4><code>stigmem://company.example/issue/EG-42</code></h4></div>
<div><h4><code>stigmem://node.acme/decision/use-sqlite</code></h4></div>

</div>

#### Deprecation of informal URIs

Informal URIs (colon-separated shorthand such as `user:alice`,
`agent:cto`) are **deprecated as of pre-reset**.

<div className="stigmem-fields">

<div>
<dt>Actor</dt>
<dt><span className="stigmem-fields__type">Requirement</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt>Nodes</dt>
<dt><span className="stigmem-fields__type">accept + warn</span></dt>
<dd>MUST accept informal URIs without rejecting (backward compatibility). MUST emit a deprecation warning to stderr when storing a fact whose <code>entity</code> or <code>source</code> field does not match the <code>stigmem://</code> scheme. MUST NOT auto-rewrite informal URIs to formal URIs on ingest.</dd>
</div>

<div>
<dt>Adapters</dt>
<dt><span className="stigmem-fields__type">use formal</span></dt>
<dd>SHOULD use formal URIs for all new fact assertions. MUST NOT emit informal URIs in new code targeting pre-reset or later.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Collision rationale.**

Informal URIs are inherently ambiguous once federation is active.
<code>user:alice</code> on node A and <code>user:alice</code> on
node B may refer to different people. The formal scheme binds the
authority to the URI, preventing silent identity collisions across
federated nodes.

</div>

**pre-reset note:** All components of the formal URI are normalized
to lowercase on ingest (§2.6). `stigmem://company.example/issue/EG-42`
is stored as `stigmem://company.example/issue/eg-42`.

### §2.6 Entity naming rules — pre-reset normative \{#section-2-6\}

This section defines canonical entity naming rules and the **strict
normalizer** contract. The goal is to prevent **silent entity
fragmentation**: multiple facts about the same real-world entity
using different URI representations that create disconnected entity
nodes in the store.

**pre-reset scope:** The strict normalizer addresses case-based and
whitespace-based fragmentation deterministically. Full alias
resolution (e.g. `user:alice` ≡ `user:a.smith`) is deferred to the
pre-reset design-partner window fuzzy resolver.

#### §2.6.1 The fragmentation problem \{#section-2-6-1\}

Before strict normalization, the following assertions create
separate entities for the same project:

```
entity="project/eg-18"                            (informal, slash separator, lowercase)
entity="project/EG-18"                            (informal, slash separator, uppercase)
entity="stigmem://company.example/project/eg-18"  (formal, lowercase id)
entity="stigmem://company.example/project/EG-18"  (formal, uppercase id)
```

All four refer to the same project. Without normalization, queries
for any one form miss the others entirely, and contradiction
detection never fires for facts that should conflict.

#### §2.6.2 Canonical form \{#section-2-6-2\}

The canonical form is the lowercase form of the URI with surrounding
whitespace trimmed and internal whitespace in the `id` component
collapsed to hyphens.

**For formal URIs (`stigmem://authority/type/id`):**

<div className="stigmem-fields">

<div>
<dt>Component</dt>
<dt><span className="stigmem-fields__type">Rule</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>authority</code></dt>
<dt><span className="stigmem-fields__type">lowercase + trim</span></dt>
<dd>Trim surrounding whitespace.</dd>
</div>

<div>
<dt><code>type</code></dt>
<dt><span className="stigmem-fields__type">lowercase + trim</span></dt>
<dd>Trim surrounding whitespace.</dd>
</div>

<div>
<dt><code>id</code></dt>
<dt><span className="stigmem-fields__type">lowercase + trim + collapse whitespace</span></dt>
<dd>Collapse internal whitespace runs to a single hyphen.</dd>
</div>

</div>

**For informal URIs (any non-`stigmem://` form):**

<div className="stigmem-grid">

<div><h4>Lowercase entire string</h4><p>Trim surrounding whitespace; collapse internal whitespace to hyphens.</p></div>
<div><h4>Format preserved</h4><p>Informal stays informal — not converted to formal.</p></div>
<div><h4>Honors §2.5 anti-rewrite</h4><p>Lowercasing the informal form is not the same as expanding it to the formal scheme.</p></div>

</div>

#### §2.6.3 Strict normalizer — normative algorithm \{#section-2-6-3\}

Reference implementation at
`stigmem/node/src/stigmem_node/entity_normalizer.py`:

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

<div className="stigmem-grid">

<div><h4>Deterministic</h4><p>Identical inputs always produce identical outputs.</p></div>
<div><h4>Idempotent</h4><p><code>normalize(normalize(x)) == normalize(x)</code> for all valid inputs.</p></div>
<div><h4>Total on valid inputs</h4><p>Every non-empty string produces exactly one output; invalid inputs raise <code>NormalizationError</code>.</p></div>

</div>

**What the strict normalizer does NOT do:**

<div className="stigmem-grid">

<div><h4>Alias resolution</h4><p><code>user:alice</code> ≡ <code>user:a.smith</code> — pre-reset design-partner fuzzy resolver.</p></div>
<div><h4>Existence validation</h4><p>Against the fact store.</p></div>
<div><h4>Semantic similarity</h4><p>Matching.</p></div>
<div><h4>Informal → formal conversion</h4><p>§2.5 prohibits silent auto-rewrite.</p></div>

</div>

#### §2.6.4 Ingest-path contract \{#section-2-6-4\}

Nodes MUST apply the strict normalizer to the `entity` and `source`
fields of every incoming fact **before** persistence:

<ol className="stigmem-steps">
<li>If <code>normalize_entity_uri</code> returns a canonical URI, store the canonical form.</li>
<li>If the input was an informal URI (does not match <code>stigmem://</code>), also emit a deprecation warning to stderr as specified in §2.5.</li>
<li>If <code>normalize_entity_uri</code> raises <code>NormalizationError</code>, reject the fact with HTTP 400 <code>{`{ "error": "invalid_entity_uri", "detail": "<NormalizationError message>" }`}</code>.</li>
</ol>

<div className="stigmem-keypoint">

**Why normalize at ingest (not query).**

Query-time normalization would require every consumer to carry
normalization logic and would leave non-canonical data permanently
in the store. Ingest normalization ensures the stored form is
always canonical; all queries use exact string matching on the
canonical form, keeping query performance O(1) on indexed lookups.

</div>

**Retraction and contradiction compatibility:** Ingest normalization
is safe for retractions (§5.4) and contradiction detection (§3.3).
If a retraction and the original fact both normalize to the same
canonical entity, they match correctly.

#### §2.6.5 Query-time backward compatibility \{#section-2-6-5\}

For nodes upgrading to pre-reset, **query parameters are also
normalized** before matching:

```
GET /v1/facts?entity=<raw>&...
```

The node MUST apply `normalize_entity_uri` to the `entity` and
`source` query parameters before executing the database query. This
allows clients holding references to pre-normalization forms to
still retrieve existing facts written after pre-reset is deployed.

For pre-pre-reset facts stored with non-canonical URIs, the alias
table (§2.6.6, migration 003) is the recommended migration path.

#### §2.6.6 Migration guide for existing facts \{#section-2-6-6\}

Facts stored before pre-reset strict normalization was deployed may
use informal URIs or non-canonical formal URIs. Because facts are
immutable (§2), they cannot be rewritten in place.

<div className="stigmem-fields">

<div>
<dt>Option</dt>
<dt><span className="stigmem-fields__type">When to use</span></dt>
<dd>How it works</dd>
</div>

<div>
<dt>A · Alias table</dt>
<dt><span className="stigmem-fields__type">recommended for production</span></dt>
<dd>Migration 003 adds an <code>entity_aliases</code> table that maps known informal/legacy URIs to their canonical equivalents (see §10). Populate by scanning the <code>facts</code> table for non-canonical values. At query time, the node joins against this table to find pre-pre-reset facts via canonical queries.</dd>
</div>

<div>
<dt>B · Re-assertion sweep</dt>
<dt><span className="stigmem-fields__type">smaller nodes / clean migration windows</span></dt>
<dd>For each fact with a non-canonical entity URI: (1) Assert a new fact with the canonical entity and same <code>(relation, value, scope, confidence)</code>, provenance <code>source="system:stigmem:migration"</code>. (2) Retract the original fact by asserting <code>confidence=0.0</code>. Originals retained with <code>confidence=0.0</code> for audit.</dd>
</div>

</div>

**Phased rollout recommendation:**

<div className="stigmem-fields">

<div>
<dt>Phase</dt>
<dt><span className="stigmem-fields__type">Window</span></dt>
<dd>Action</dd>
</div>

<div>
<dt>pre-reset deploy</dt>
<dt><span className="stigmem-fields__type">T+0</span></dt>
<dd>Enable strict normalizer on ingest. Query normalization enabled.</dd>
</div>

<div>
<dt>Scan + alias</dt>
<dt><span className="stigmem-fields__type">T+2 weeks</span></dt>
<dd>Scan facts table; populate alias table for any non-canonical existing facts.</dd>
</div>

<div>
<dt>Re-assertion sweep</dt>
<dt><span className="stigmem-fields__type">T+4 weeks</span></dt>
<dd>For nodes with &lt; 10k facts; otherwise maintain alias table.</dd>
</div>

<div>
<dt>Alias removal</dt>
<dt><span className="stigmem-fields__type">pre-reset spec target</span></dt>
<dd>Remove alias table read path; all facts use canonical URIs.</dd>
</div>

</div>

### §2.7 Garden field \{#section-2-7\}

An optional `garden_id` field on a fact associates it with a Memory
Garden (§17).

```
FactRecord (the pre-reset spec extension):
  ...all the pre-reset spec fields...
  garden_id: URI | null    // stigmem://authority/garden/{slug}; null = no garden
  attested:  boolean | null  // source attestation result (§18); null = not applicable
```

**`garden_id` invariant.** When `garden_id` is set:

<ol className="stigmem-steps">
<li>The garden MUST exist on the local node.</li>
<li>The writing principal MUST hold <code>writer</code> or <code>admin</code> role in the garden.</li>
<li>The fact's <code>scope</code> MUST equal the garden's declared <code>scope</code>.</li>
<li>Garden-tagged facts are subject to garden ACL at read time (§17.3).</li>
</ol>

**`garden_id` on federation.** Garden membership is node-local.
Facts with `garden_id` set MUST NOT be replicated to peers. Nodes
MUST silently drop `garden_id` from federated facts they receive.

**`attested` semantics:**

<div className="stigmem-fields">

<div>
<dt>Value</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>true</code></dt>
<dt><span className="stigmem-fields__type">verified</span></dt>
<dd>Node verified that <code>source</code> equals the caller's authenticated <code>entity_uri</code>.</dd>
</div>

<div>
<dt><code>false</code></dt>
<dt><span className="stigmem-fields__type">mismatch</span></dt>
<dd>Source/identity mismatch detected; fact accepted in <code>warn</code> or <code>off</code> mode.</dd>
</div>

<div>
<dt><code>null</code></dt>
<dt><span className="stigmem-fields__type">not applicable</span></dt>
<dd>Auth disabled, federation ingest, or system fact.</dd>
</div>

</div>

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

</details>

### §2.8 Federation trust fields \{#section-2-8\}

Three optional fields extend the fact record to carry provenance,
attestation evidence, and source-trust information.

```
FactRecord (v0.9.0a1):
  ...all canonical FactRecord fields...
  derived_from:      [FactHash]  | null  // provenance: hashes of facts this derives from (§19.6)
  attestation_chain: [Signature] | null  // ordered attestation signatures (§19.6)
  source_trust:      float | null        // cached source-trust score at write time (§19.4); null = not computed
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Semantics</dd>
</div>

<div>
<dt><code>derived_from</code></dt>
<dt><span className="stigmem-fields__type">[FactHash] | null</span></dt>
<dd>Hex-encoded SHA-256 hashes of antecedent facts. Ordered by logical derivation; first entry is most direct.</dd>
</div>

<div>
<dt><code>attestation_chain</code></dt>
<dt><span className="stigmem-fields__type">[Signature] | null</span></dt>
<dd>Base64url-encoded Ed25519 signatures from org manifest keys. Ordered from innermost to outermost signer; empty array equivalent to <code>null</code>.</dd>
</div>

<div>
<dt><code>source_trust</code></dt>
<dt><span className="stigmem-fields__type">float [0.0, 1.0] | null</span></dt>
<dd>Cached source-trust score at write time (§19.4). Nodes SHOULD populate when computation enabled. Nodes MUST NOT reject facts with a low value at write time; the value is informational. Recomputed at recall time — MUST NOT be relied upon as final from the stored record; stored value is a snapshot for audit.</dd>
</div>

</div>
