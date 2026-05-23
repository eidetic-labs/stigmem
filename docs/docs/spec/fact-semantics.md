---
title: Spec-15 Fact Semantics
sidebar_label: Spec-15 Fact Semantics
audience: Spec
description: "Spec-15-Fact-Semantics rendered entry point — provenance, expiry, retraction, contradiction, and conflict entities."
---

# Spec-15-Fact-Semantics \{#section-3\}

<p className="stigmem-meta"><span>5 min read</span><span>Spec contributor · Implementer</span><span>Read/write semantics</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-15-Fact-Semantics`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/15-fact-semantics.md).
Read/write semantics, retraction, contradiction, identity binding.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Legacy §3 anchors are retained for existing links while the maintained
prose lives in `Spec-15-Fact-Semantics`.
:::

### §3.1 Provenance \{#section-3-1\}

Every fact carries `source` and `timestamp`. A node MUST store both
without modification. Clients querying facts MUST receive the
original source, not the relay chain.

**Federated provenance:** Inbound federated facts MUST additionally
carry a `stigmem:received_from` meta-fact (asserted automatically by
the receiving node):

```
(entity=<fact-id>, relation="stigmem:received_from",
 value={type:"ref", v:"<originating-node-id>"},
 source="system:stigmem", ...)
```

This meta-fact is stored locally and MUST NOT be re-replicated.

### §3.2 Decay and temporal scope \{#section-3-2\}

<div className="stigmem-fields">

<div>
<dt>Concept</dt>
<dt><span className="stigmem-fields__type">Mechanism</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>valid_until</code></dt>
<dt><span className="stigmem-fields__type">field-level expiry</span></dt>
<dd>Facts whose <code>valid_until</code> has passed MUST NOT be returned unless the caller sends <code>include_expired=true</code>. Expired facts remain in the store.</dd>
</div>

<div>
<dt>TTL meta-fact</dt>
<dt><span className="stigmem-fields__type">retroactive expiry</span></dt>
<dd>Schedule a future expiry on a fact originally asserted without <code>valid_until</code> by attaching a meta-fact in the reserved <code>stigmem:ttl</code> namespace. The decay sweeper honours TTL meta-facts during its sweep pass.</dd>
</div>

<div>
<dt><code>valid_until</code> vs. <code>confidence</code></dt>
<dt><span className="stigmem-fields__type">orthogonal</span></dt>
<dd>A historical certain fact has <code>confidence=1.0</code> and <code>valid_until</code> set to when it was superseded.</dd>
</div>

</div>

```
(entity=<fact-id>, relation="stigmem:ttl", value={type:"datetime", v:<expiry>}, ...)
```

**Decay sweeper (pre-reset):** For operator-managed confidence decay
over time, see §15.

### §3.3 Contradiction — pre-reset formalized \{#section-3-3\}

A **contradiction** exists when two facts `a`, `b` satisfy all of:

<div className="stigmem-grid">

<div><h4>Same entity</h4><p><code>a.entity == b.entity</code></p></div>
<div><h4>Same relation</h4><p><code>a.relation == b.relation</code></p></div>
<div><h4>Same scope</h4><p><code>a.scope == b.scope</code></p></div>
<div><h4>Different values</h4><p><code>a.value != b.value</code></p></div>
<div><h4>Both live</h4><p><code>a.confidence &gt; 0.0 && b.confidence &gt; 0.0</code></p></div>

</div>

<div className="stigmem-keypoint">

**Both facts are retained. Neither is silently overwritten.**

</div>

**pre-reset note:** Because `entity` is normalized on ingest (§2.6),
two facts about the same real-world entity written with different
cases (e.g. `project/EG-18` vs `project/eg-18`) now normalize to the
same canonical entity and correctly trigger contradiction detection.
Pre-pre-reset fragmented facts are not retroactively merged — use the
alias table or re-assertion sweep (§2.6.6) to consolidate them.

**Resolution order at query time:**

<ol className="stigmem-steps">
<li>Higher <code>confidence</code> wins.</li>
<li>Equal confidence → higher <code>hlc</code> wins (causal ordering).</li>
<li>Tie → both returned with <code>contradicted: true</code> on each; caller decides.</li>
</ol>

**Contradiction fact (pre-reset):** When a contradiction is detected
on write, the node MUST assert a system-generated contradiction
record:

```
POST /v1/facts  (system-generated, source="system:stigmem")
{
  "entity":   "stigmem:conflict:<uuid>",
  "relation": "stigmem:conflict:between",
  "value":    { "type": "text", "v": "<fact-id-a> <fact-id-b>" },
  "source":   "system:stigmem",
  "confidence": 1.0,
  "scope":    <same scope as the conflicting facts>
}
```

A second fact records the conflict's resolution state. It starts as
`"unresolved"` and transitions to `"resolved"` when a caller invokes
the conflict resolution endpoint (§5.10):

```
(entity="stigmem:conflict:<uuid>", relation="stigmem:conflict:status",
 value={type:"string", v:"unresolved"}, ...)
```

**Conflict entities** are queryable at `GET /v1/conflicts` (§5.9).

**Resolution:** A human or agent resolves via
`POST /v1/conflicts/:id/resolve` (§5.10). The resolution is itself a
new fact with provenance; the conflict status is updated to
`"resolved"`.

### §3.4 Scope enforcement \{#section-3-4\}

Scope is enforced at read and write time. Cross-scope queries are
additive.

**Federation enforcement:** Nodes MUST reject outbound replication of
facts whose scope is not permitted by the active PeerDeclaration.
Nodes MUST reject inbound facts whose scope exceeds what the peer is
authorized to write. See §6.4.

**the pre-reset spec note:** In N-node topologies, scope enforcement
is per-hop, not end-to-end. See §6.8 for the transitive scope
propagation invariant that closes the re-federation gap.

### §3.5 Identity and auth — source attestation \{#section-3-5\}

*Prior content (API-key model, per-scope key restrictions, federation
peer tokens) unchanged from the pre-reset spec.*

#### Source attestation

<div className="stigmem-keypoint">

**Problem.** In the pre-reset spec, the <code>source</code> URI in a
fact's request body is caller-declared. An authenticated principal
can claim to be anyone by writing
<code>"source": "stigmem://authority/user/someone-else"</code>. This
breaks provenance guarantees.

</div>

**Current alpha solution:** Source attestation is owned by
`stigmem-plugin-source-attestation`. When the plugin is registered and
the assertion-validation gate is enabled, it validates the declared
`source` against the caller's `entity_uri` plus any explicitly exposed
delegation list.

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Posture</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt><code>enforce</code></dt>
<dt><span className="stigmem-fields__type">strict</span></dt>
<dd>Plugin-loaded deployments reject any <code>POST /v1/facts</code> where <code>source ∉ {`{identity.entity_uri}`} ∪ identity.allowed_source_entities</code>. Returns <code>source_attestation_failed</code>.</dd>
</div>

<div>
<dt><code>warn</code></dt>
<dt><span className="stigmem-fields__type">observed</span></dt>
<dd>Compatibility posture retained from the pre-reset design. Warn-mode persistence is not implemented by the current alpha plugin.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">disabled (default)</span></dt>
<dd>No attestation check. <code>attested: null</code> on all records.</dd>
</div>

</div>

**Default mode:** `off`. Default installs do not apply
source-attestation behavior; runtime enforcement is owned by
`stigmem-plugin-source-attestation` and requires explicit plugin
gates. Single-operator deployments that trust all their callers do
not need to enable the plugin. Production multi-tenant deployments
SHOULD enable plugin enforcement once source bindings are verified.

**Node configuration:** `STIGMEM_SOURCE_ATTESTATION_MODE` is a legacy
compatibility field. Nodes expose the configured compatibility value
at `/.well-known/stigmem` as
`"source_attestation": "enforce" | "warn" | "off"`.

**Auth-disabled mode:** When `STIGMEM_AUTH_REQUIRED=false`, the caller identity
is anonymous. Source-attestation checks only run if the plugin is registered
and the relevant gate is enabled; otherwise `attested` remains `null`.

**Service agents writing on behalf of others:** `allowed_source_entities`
delegates specific source claims when that metadata is available on the
resolved identity. Durable API-backed delegation-list persistence remains
future hardening work.

**Federated facts:** Source attestation is not re-applied to facts received via
federation. The plugin can guard inbound peer/source consistency, but the
original `source` is preserved per §3.1 and federated facts are not silently
re-attested as local assertions.

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft, pre-reset draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

### 3.5 Identity and Auth (pre-reset extended)

**Status:** pre-reset API-key model implemented. pre-reset extension with per-scope key
restrictions and peer-token auth for federation.

#### Identity shape

An `Identity` binds a credential (API key) to an entity URI and constrains
which scopes that credential may access. The `entity_uri` field becomes the
`source` on any fact asserted with this key — this is how Stigmem attributes
assertions to their originator and enables provenance queries ("which agent
asserted this?").

```
Identity {
  entity_uri:     URI
  credential:     string          // API key (Argon2id stored server-side)
  node_url:       string
  allowed_scopes: FactScope[]     // pre-reset: restricts which scopes this key can read/write
}
```

**Per-scope key restrictions (pre-reset):** `api_keys` MUST store `allowed_scopes`. Default
is `["local","team","company","public"]` (all scopes) for backward compatibility.
Additive model: if `allowed_scopes` is empty, the key has no access. Operators SHOULD
restrict service-to-service keys to the minimum required scope.

#### pre-reset API-key model (unchanged)

Credentials are presented as `Authorization: Bearer <raw-key>`. The node stores only
the Argon2id hash. Legacy v0.9.0a1 SHA-256 rows remain readable during the
v0.9.x migration window and rehash on successful use.

**Auth mode flag:** `/.well-known/stigmem` exposes `"auth": "none" | "required"`.

#### Federation peer tokens (pre-reset)

Federated replication uses short-lived **peer tokens** distinct from API keys:

```
PeerToken {
  iss:      URI          // issuing node_id
  sub:      URI          // target node_id
  iat:      epoch_ms
  exp:      epoch_ms     // MUST be ≤ iat + 3600000 (1 hour)
  nonce:    UUID         // replay protection
  scopes:   FactScope[]  // permitted scopes for this token
}
```

Tokens are Ed25519-signed JWTs. The signing key is the node's federation keypair
(separate from API keys; published at `/.well-known/stigmem` as `federation_pubkey`).

Receiving nodes MUST verify:
1. Signature against `iss` node's `federation_pubkey` (fetched at peer registration, cached).
2. `sub` matches the receiving node's own `node_id`.
3. `exp` has not passed.
4. `nonce` has not been seen within the node's nonce window (default: 5 minutes).

---

**From `stigmem-spec-pre-reset draft.md`:**

### 3.5 Identity and Auth — Source Attestation (the pre-reset spec extension)

*Prior content (API-key model, per-scope key restrictions, federation peer tokens) unchanged from the pre-reset spec.*

#### Source attestation

**Problem:** In the pre-reset spec, the `source` URI in a fact's request body is caller-declared. An authenticated principal can claim to be anyone by writing `"source": "stigmem://authority/user/someone-else"`. This breaks provenance guarantees — a fact's `source` field cannot be trusted as the actual write origin without an out-of-band verification.

**Solution (pre-reset):** Source attestation binds the declared `source` to the caller's `entity_uri` registered on their API key at write time (§18.7). The `entity_uri` is immutable after key creation. The binding is enforced by the node in one of three modes:

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

| Mode      | Behavior |
|-----------|---------|
| `enforce` | Node rejects any `POST /v1/facts` where `source ∉ {identity.entity_uri} ∪ identity.allowed_source_entities`. Returns HTTP 403 `source_attestation_failed`. |
| `warn`    | Node accepts the fact; logs a warning; sets `attested: false` on the stored record. |
| `off`     | No attestation check. `attested: null` on all records. |

**Default mode:** `off`. Default installs do not apply source-attestation behavior; runtime enforcement is owned by `stigmem-plugin-source-attestation` and requires explicit plugin gates. Single-operator deployments that trust all their callers do not need to enable the plugin. Production multi-tenant deployments SHOULD enable plugin enforcement once source bindings are verified.

**Node configuration:** `STIGMEM_SOURCE_ATTESTATION_MODE` is a legacy compatibility field. Nodes expose the configured compatibility value at `/.well-known/stigmem` as `"source_attestation": "enforce" | "warn" | "off"`.

**Auth-disabled mode:** When `STIGMEM_AUTH_REQUIRED=false`, the caller identity is anonymous. Attestation cannot be performed; `attested` is `null` for all writes in this mode.

**Service agents writing on behalf of others:** Use `allowed_source_entities` (§18.9) to delegate specific source claims to an adapter key. This is the explicit delegation path — the pre-reset spec model does not support implicit delegation.

**Federated facts:** Source attestation is NOT re-applied to facts received via federation. The original `source` is preserved per §3.1. Federated facts MUST have `attested: null` on ingest.

</details>
