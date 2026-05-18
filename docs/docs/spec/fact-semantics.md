---
title: Spec-15 Fact Semantics
sidebar_label: Spec-15 Fact Semantics
audience: Spec
description: "Spec-15-Fact-Semantics rendered entry point — provenance, expiry, retraction, contradiction, and conflict entities."
---

# Spec-15-Fact-Semantics {#section-3}

**Status:** Rendered compatibility entry point for [`Spec-15-Fact-Semantics`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/15-fact-semantics.md).

Read/write semantics, retraction, contradiction, identity binding.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

Legacy §3 anchors are retained for existing links while the maintained prose lives in `Spec-15-Fact-Semantics`.

### §3.1 Provenance {#section-3-1}

Every fact carries `source` and `timestamp`. A node MUST store both without
modification. Clients querying facts MUST receive the original source, not the
relay chain.

**Federated provenance:** Inbound federated facts MUST additionally carry a
`stigmem:received_from` meta-fact (asserted automatically by the receiving node):

```
(entity=<fact-id>, relation="stigmem:received_from",
 value={type:"ref", v:"<originating-node-id>"},
 source="system:stigmem", ...)
```

This meta-fact is stored locally and MUST NOT be re-replicated.

### §3.2 Decay and Temporal Scope {#section-3-2}

**`valid_until`:** Facts whose `valid_until` has passed MUST NOT be returned unless
the caller sends `include_expired=true`. Expired facts remain in the store.

**TTL meta-fact:** Operators or agents that want to schedule a future expiry on
a fact that was originally asserted without `valid_until` can attach one
retroactively via a TTL meta-fact. The meta-fact's entity is the target fact's
ID; the relation uses the reserved `stigmem:ttl` namespace; and the value is
the intended expiry datetime. The decay sweeper (§15) honours TTL meta-facts
during its sweep pass.

```
(entity=<fact-id>, relation="stigmem:ttl", value={type:"datetime", v:<expiry>}, ...)
```

**`valid_until` vs. `confidence`:** Orthogonal. A historical certain fact has
`confidence=1.0` and `valid_until` set to when it was superseded.

**Decay sweeper (pre-reset):** For operator-managed confidence decay over time, see §15. The decay sweeper handles gradual confidence reduction and bulk TTL retraction without requiring clients to manage each fact's expiry individually.

### §3.3 Contradiction — pre-reset formalized {#section-3-3}

A **contradiction** exists when two facts `a`, `b` satisfy all of:
- `a.entity == b.entity`
- `a.relation == b.relation`
- `a.scope == b.scope`
- `a.value != b.value`
- `a.confidence > 0.0 && b.confidence > 0.0`

**Both facts are retained. Neither is silently overwritten.**

**pre-reset note:** Because `entity` is normalized on ingest (§2.6), two facts about the same real-world entity written with different cases (e.g. `project/EG-18` vs `project/eg-18`) now normalize to the same canonical entity and correctly trigger contradiction detection. Pre-pre-reset fragmented facts are not retroactively merged — use the alias table or re-assertion sweep (§2.6.6) to consolidate them.

**Resolution order at query time:**
1. Higher `confidence` wins.
2. Equal confidence → higher `hlc` wins (causal ordering).
3. Tie → both returned with `contradicted: true` on each; caller decides.

**Contradiction fact (pre-reset):** When a contradiction is detected on write, the
node MUST assert a system-generated contradiction record. The contradiction is
itself a first-class entity in the `stigmem:conflict:` namespace — this reifies
the disagreement as queryable data rather than hiding it in a separate table.
The `stigmem:conflict:between` fact links the two competing fact IDs; a
companion status fact tracks whether the contradiction has been resolved.

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
`"unresolved"` and transitions to `"resolved"` when a caller invokes the
conflict resolution endpoint (§5.10):

```
(entity="stigmem:conflict:<uuid>", relation="stigmem:conflict:status",
 value={type:"string", v:"unresolved"}, ...)
```

**Conflict entities** are queryable at `GET /v1/conflicts` (§5.9).

**Resolution:** A human or agent resolves via `POST /v1/conflicts/:id/resolve` (§5.10).
The resolution is itself a new fact with provenance; the conflict status is updated to
`"resolved"`.

### §3.4 Scope Enforcement {#section-3-4}

Scope is enforced at read and write time. Cross-scope queries are additive.

**Federation enforcement:** Nodes MUST reject outbound replication of facts whose
scope is not permitted by the active PeerDeclaration. Nodes MUST reject inbound
facts whose scope exceeds what the peer is authorized to write. See §6.4.

**the pre-reset spec note:** In N-node topologies, scope enforcement is per-hop, not end-to-end. See §6.8 for the transitive scope propagation invariant that closes the re-federation gap.

### §3.5 Identity and Auth — Source Attestation {#section-3-5}

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

---

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

---

</details>
