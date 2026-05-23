---
spec_id: Spec-X6-Source-Attestation
version: 0.1.0-alpha.0
status: Experimental
applies_to: experimental plugin line
last_updated: 2026-05-23
supersedes: pre-reset section 18 source-attestation material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-09-Audit-Log >= 0.1.0-alpha.0
title: Spec-X6-Source-Attestation
sidebar_label: Source Attestation
audience: Spec
description: "Opt-in plugin validation of fact source claims, recall rank contribution, and federation source guards."
stability: experimental
since: 0.9.0a1
---

# Spec-X6-Source-Attestation: Source Attestation {#section-18}

<p className="stigmem-meta"><span>6 min read</span><span>Spec contributor · Node operator</span><span>Experimental · opt-in plugin line</span></p>

<div className="stigmem-lead">

**What this spec defines**

Opt-in plugin validation of caller-declared fact `source` values. The current
alpha plugin validates direct and delegated source claims, recall source-trust
contribution, and federation source guards without changing the default install
or proving release artifact provenance.

</div>

**Status:** Experimental / opt-in source package on `main`

**Implementation state:** `stigmem-plugin-source-attestation` lives under
`experimental/source-attestation/` and registers `pre_assert_validate`,
`recall_rank`, and `federation_inbound_validate` hook handlers. Default installs
keep source-attestation behavior inert; operators must register the plugin and
enable the relevant `STIGMEM_SOURCE_ATTESTATION_*` gates before enforcement or
ranking behavior runs.

**Artifact state:** signed/package publication remains deferred to the
all-plugins launch lane.

**Current alpha limits:** the plugin validates source claims but does not set
`attested: true` on accepted facts, does not persist warn-mode `attested: false`
outcomes, and does not re-attest inbound federated facts as local assertions.
Durable API-backed delegation persistence and key-rotation conformance remain
future hardening work.

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

### Spec-X6-Source-Attestation section 1 Motivation {#section-18-1}

In the pre-reset source-attestation design, the `source` field in a fact request body is caller-declared:

```json
{ "entity": "...", "relation": "...", "source": "stigmem://node/user/alice", ... }
```

<div className="stigmem-keypoint">

**Nothing prevents an `agent:assistant` principal from writing `"source": "stigmem://node/user/bob"`.**

The stored fact will falsely attribute its origin to Bob. This
undermines audit trails (who actually wrote this fact?), trust
scoring (confidence in a fact depends on who asserted it), and
Track C's keypair-signed attribution model.

</div>

Source attestation closes this gap by binding `source` to the verified `entity_uri` from the auth principal at write time.

### Spec-X6-Source-Attestation section 2 Attestation Model {#section-18-2}

When a fact is asserted with auth enabled and the plugin assertion gate is
explicitly enabled, the node:

<ol className="stigmem-steps">
<li>Resolves the key's registered <code>entity_uri</code> and <code>allowed_source_entities</code> (Spec-X6-Source-Attestation section 7).</li>
<li>Normalizes <code>fact.source</code> and all entries in the authorized set using Spec-01-Fact-Model URI normalization.</li>
<li>Checks <code>attested = normalized(fact.source) ∈ &#123; normalized(identity.entity_uri) &#125; ∪ normalized(identity.allowed_source_entities)</code>.</li>
</ol>

Default installs do not run this check. The current alpha plugin expects the
asserted fact source to be present in the request and validates it before core
persistence.

```
SourceAttestationMode = "enforce" | "warn" | "off"
```

<div className="stigmem-fields">

<div>
<dt>Mode</dt>
<dt><span className="stigmem-fields__type">Behavior</span></dt>
<dd>On mismatch / no entity</dd>
</div>

<div>
<dt><code>enforce</code></dt>
<dt><span className="stigmem-fields__type">strict</span></dt>
<dd>When the plugin is registered and <code>STIGMEM_SOURCE_ATTESTATION_ENFORCE_ASSERT_VALIDATION=true</code>, any <code>source</code> outside <code>&#123;entity_uri&#125; ∪ allowed_source_entities</code> causes <code>source_attestation_failed</code>. Accepted facts are not marked <code>attested: true</code> in the current alpha plugin.</dd>
</div>

<div>
<dt><code>warn</code></dt>
<dt><span className="stigmem-fields__type">log only</span></dt>
<dd>Compatibility posture retained from the pre-reset design. Warn-mode logging and <code>attested: false</code> persistence are not implemented by the current alpha plugin.</dd>
</div>

<div>
<dt><code>off</code></dt>
<dt><span className="stigmem-fields__type">disabled</span></dt>
<dd>No check. <code>attested: null</code> on all facts.</dd>
</div>

</div>

**Default-install behavior:** default installs use inert behavior. The legacy `STIGMEM_SOURCE_ATTESTATION_MODE` compatibility value is advertised at `/.well-known/stigmem`, but the runtime checks above require `stigmem-plugin-source-attestation` plus explicit plugin gates.

### Spec-X6-Source-Attestation section 3 Well-Known Advertisement {#section-18-3}

Nodes MUST advertise their attestation mode at `/.well-known/stigmem`:

```json
{
  ...existing fields...,
  "source_attestation": "enforce" | "warn" | "off"
}
```

Clients SHOULD read this before writing to understand whether their `source` claim will be enforced.

### Spec-X6-Source-Attestation section 4 Attestation and Retraction {#section-18-4}

<div className="stigmem-keypoint">

**Retractions are subject to the same attestation rules as any other fact write.**

A fact written by `agent:assistant` can only be retracted by
`agent:assistant` in `enforce` mode (since the source must match the
caller). If the original writer is no longer available, node admins
must temporarily set `warn` or `off` mode to perform administrative
retractions.

</div>

### Spec-X6-Source-Attestation section 5 Integration with Track C (Per-Agent Keypairs) {#section-18-5}

Track C adds per-agent keypair registration. Once an agent's public key is registered on the node, a stronger form of attestation becomes possible: the agent signs the fact payload before submission, and the node verifies the signature against the registered public key. This moves attestation from "bearer-token-level" (who presented this API key?) to "fact-level" (who signed this specific fact payload?).

Source attestation is a first step toward fact-level attribution. The current
alpha plugin validates bearer-token-level source authorization but does not set
`attested: true` on accepted facts. Track C extends this direction with
separate signature verification once keypairs are implemented.

### Spec-X6-Source-Attestation section 6 Querying by Attestation {#section-18-6}

Facts can be filtered by the compatibility `attested` field:

```
GET /v1/facts?attested=true    // facts explicitly marked attested
GET /v1/facts?attested=false   // facts explicitly marked unattested
```

The current alpha source-attestation plugin leaves accepted facts with
`attested: null`; the query parameter remains for schema compatibility and
future posture work. Omitting it returns all facts.

### Spec-X6-Source-Attestation section 7 Key Registration: Binding `entity_uri` to an API Key {#section-18-7}

Source attestation depends on the node knowing the caller's authorized `entity_uri`. This binding is established at **key creation time** and is immutable — a key's `entity_uri` cannot be changed after creation (to prevent retroactive provenance forgery).

**Current alpha state:** core API keys bind `entity_uri` and permissions today.
The source-attestation plugin also accepts `allowed_source_entities` when that
metadata is present on the resolved identity object, but durable API-backed
delegation-list persistence is not complete in this release horizon.

<div className="stigmem-grid">

<div><h4>Formal URI</h4><p>MUST be a formal URI matching the <code>stigmem://</code> scheme. Informal URIs are rejected at key creation.</p></div>
<div><h4>Unique per node</h4><p>MUST be unique within the node's <code>api_keys</code> table (one key per entity).</p></div>
<div><h4>Normalized at storage</h4><p>Stored in normalized form to align with ingest normalization.</p></div>

</div>

#### Key creation

A key is created with a single POST that binds the `entity_uri` and
permissions. The node returns the raw API key exactly once in the response;
new keys are stored with Argon2id hashes. Legacy SHA-256 hashes are accepted
only during the configured migration window.

```
POST /v1/auth/keys
Authorization: Bearer <admin-key>
{
  "description":             "CTO agent key",
  "entity_uri":              "stigmem://company.example/agent/cto",
  "allowed_scopes":          ["company", "public"],
  "allowed_source_entities": []
}
→ 201 {
    "key_id":                  "<uuid>",
    "raw_key":                 "<secret>",   // shown once; verifier stored
    "entity_uri":              "stigmem://company.example/agent/cto",
    "allowed_scopes":          ["company","public"],
    "allowed_source_entities": [],
    "created_at":              "2026-05-03T00:00:00Z"
  }
```

<div className="stigmem-keypoint">

**The caller MUST store `raw_key` securely — it is not retrievable after creation.**

The node stores only a verifier, never the raw key. `entity_uri` is immutable
after creation; changing source identity requires revoking and recreating the
key.

</div>

**Creating a key without `entity_uri`** is allowed for backward compatibility.
Such a key can still write facts when source-attestation enforcement is not
enabled. When plugin enforcement is enabled, source validation requires a
resolved identity source or explicit delegated source metadata.

#### Updated `Identity` shape

```
Identity {
  entity_uri:              URI            // registered at key creation; enforced against fact.source
  credential:              string         // raw API key is never stored
  node_url:                string
  allowed_scopes:          FactScope[]
  allowed_source_entities: URI[]          // additional source URIs this key may claim
}
```

### Spec-X6-Source-Attestation section 8 Source Auto-fill {#section-18-8}

Source auto-fill is retained as pre-reset design context but is not claimed as
implemented by the current alpha plugin. In v0.9.0a7 validation, default
installs remain inert and plugin-loaded enforcement validates the `source`
presented to the assertion hook.

```
POST /v1/facts
{ "entity": "stigmem://company.example/user/alice", "relation": "memory:role",
  "value":  { "type": "string", "v": "CEO" },
  "confidence": 1.0, "scope": "company" }
  // source omitted

→ current alpha behavior depends on the core assertion request contract;
  source-attestation does not auto-mark the result as locally attested.
```

Warn-mode response headers, `source_required`, and `key_not_attested` storage
outcomes remain future hardening work unless implemented by a later plugin
revision.

### Spec-X6-Source-Attestation section 9 Delegation via `allowed_source_entities` {#section-18-9}

Some adapters write facts on behalf of other principals. The Paperclip hook, for example, writes facts with `source="stigmem://company.example/agent/cto"` while running inside an agent's context — but the adapter's own key may be bound to `stigmem://company.example/adapter/paperclip`.

A key's `allowed_source_entities` is an explicit allowlist of additional URIs the key is authorized to claim as `source`:

```json
{
  "entity_uri":              "stigmem://company.example/adapter/paperclip",
  "allowed_source_entities": [
    "stigmem://company.example/agent/cto",
    "stigmem://company.example/agent/qa"
  ]
}
```

<div className="stigmem-keypoint">

**Delegation is not transitive.**

If key K1 (entity E1) has E2 in `allowed_source_entities`, K1 can
claim E1 or E2, but this grants K1 no rights to entities that E2's
own key delegates. `allowed_source_entities` defaults to `[]` — every
delegation must be an explicit operator grant.

</div>

### Spec-X6-Source-Attestation section 10 Full Key Management API {#section-18-10}

Full source-attestation key-management and attestation-audit routes remain
pre-reset design context. Current alpha validation uses the existing API-key
auth surface plus plugin hook validation; standalone attestation audit routes
are not claimed as shipped source-attestation behavior.

```
POST   /v1/auth/keys                             // create key
GET    /v1/auth/keys                             // list all keys
GET    /v1/auth/keys/:key_id                     // get key metadata
PATCH  /v1/auth/keys/:key_id                     // update description, allowed_scopes, allowed_source_entities
DELETE /v1/auth/keys/:key_id                     // revoke key (sets revoked_at; record retained for audit)

GET    /v1/auth/attestation-audit                // future attestation event log
```

Future revisions may allow `description`, `allowed_scopes`, and
`allowed_source_entities` updates while keeping `entity_uri` immutable.
Current alpha evidence does not claim durable API-backed delegation persistence
or warn-mode attestation audit events.

The attestation-audit query shape below is future design context, not a
v0.9.0a7 shipped route.

### Spec-X6-Source-Attestation section 11 Schema Migration (Migration 005) {#section-18-11}

The pre-reset design used a dedicated source-attestation migration. Current
alpha validation does not add a source-attestation-specific schema migration;
the core `facts.attested` compatibility column remains available, and the
plugin records its current behavior through tests and feature evidence.

```sql
-- API key management
CREATE TABLE IF NOT EXISTS api_keys (
  id                      TEXT PRIMARY KEY,
  description             TEXT,
  credential_hash         TEXT NOT NULL UNIQUE,
  entity_uri              TEXT,
  allowed_scopes          TEXT NOT NULL DEFAULT '["local","team","company","public"]',
  allowed_source_entities TEXT NOT NULL DEFAULT '[]',
  admin                   INTEGER NOT NULL DEFAULT 0,
  created_at              TEXT NOT NULL,
  revoked_at              TEXT
);

CREATE INDEX IF NOT EXISTS idx_api_keys_credential ON api_keys(credential_hash);
CREATE INDEX IF NOT EXISTS idx_api_keys_entity_uri ON api_keys(entity_uri);

-- Attestation audit log
CREATE TABLE IF NOT EXISTS attestation_audit (
  id               TEXT PRIMARY KEY,
  key_id           TEXT NOT NULL REFERENCES api_keys(id),
  entity_uri       TEXT,
  claimed_source   TEXT NOT NULL,
  attested         INTEGER NOT NULL,
  rejection_reason TEXT,
  ts               TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_attestation_audit_key_ts   ON attestation_audit(key_id, ts);
CREATE INDEX IF NOT EXISTS idx_attestation_audit_attested ON attestation_audit(attested, ts);
```

**Migration note for existing deployments:**

<ol className="stigmem-steps">
<li>Leave default-install source-attestation behavior inert unless <code>stigmem-plugin-source-attestation</code> is registered.</li>
<li>Verify every caller has the expected <code>entity_uri</code> before enabling assertion enforcement.</li>
<li>Treat durable delegation lists, warn-mode audit evidence, and key-rotation conformance as future hardening work until they are implemented and tested.</li>
</ol>

### Spec-X6-Source-Attestation section 12 Error Reference {#section-18-12}

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>source_required</code></span></dt>
<dd>Future hardening: source omitted while strict attestation requires a source.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>key_not_attested</code></span></dt>
<dd>Future hardening: key lacks source-binding metadata required by policy.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type"><code>source_attestation_failed</code></span></dt>
<dd><code>source</code> not in <code>&#123;entity_uri&#125; ∪ allowed_source_entities</code> when the plugin enforcement gate is enabled.</dd>
</div>

<div>
<dt>422</dt>
<dt><span className="stigmem-fields__type"><code>immutable_field</code></span></dt>
<dd>Future hardening: attempt to change immutable source-binding metadata.</dd>
</div>

</div>

---
