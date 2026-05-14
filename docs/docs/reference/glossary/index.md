---
title: Glossary
sidebar_label: Glossary
description: Definitions of key terms used in the Stigmem protocol and documentation.
---

# Glossary

Canonical definitions for terms used throughout the Stigmem protocol specification and documentation. Each entry cites the relevant modular spec.

---

## Capability Token {#capability-token}

A signed, short-lived credential that grants a specific named permission (verb) to a specific subject from a specific issuer. Capability tokens replace ad-hoc per-peer trust agreements with a verifiable, revocable, auditable delegation primitive. Each token carries an Ed25519 signature, a `verb` (`read`, `write`, `admin`, `federate`, `subscribe`, `tombstone:read`), an `object` (the resource it applies to), and a mandatory expiry (max 90 days).

**Spec:** `Spec-06-Capability-Tokens`

```json
{
  "token_id": "a1b2c3d4-...",
  "issuer": "stigmem://node.acme.example",
  "subject": "stigmem://node.acme.example/user/alice",
  "verb": "write",
  "object": "stigmem://node.acme.example/scope/company",
  "expiry": "2026-08-01T00:00:00Z"
}
```

---

## CID (Content Identifier) {#cid}

A content-addressed hash that uniquely identifies a fact by its canonical body. Computed as `sha256:` followed by the hex-encoded SHA-256 digest of the fact's deterministic canonical JSON serialization. CIDs enable deduplication, tamper detection, and idempotent federation ingestion without requiring a central ID authority.

**Spec:** `Spec-21-Content-Addressed-IDs`

```
sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

---

## Fact {#fact}

The atomic unit of knowledge in Stigmem. A fact is an immutable tuple:

```
(entity, relation, value, source, timestamp, hlc, confidence, scope)
```

Facts are append-only — there is no `PUT` or `DELETE`. Updating a value means asserting a new fact; the latest fact for a given `(entity, relation, scope)` triple wins by precedence rules. A fact with `confidence = 0.0` is a retraction.

**Spec:** `Spec-01-Fact-Model`

```json
{
  "entity": "stigmem://node/user/alice",
  "relation": "memory:role",
  "value": { "type": "string", "v": "engineer" },
  "source": "stigmem://node/agent/onboarding",
  "confidence": 1.0,
  "scope": "company"
}
```

---

## Garden {#garden}

A named, ACL-controlled partition within a scope. Gardens provide fine-grained access control above the four-level scope hierarchy (`local`, `team`, `company`, `public`). Each garden has a `slug`, a fixed `scope`, and a membership list of principals with roles (`admin`, `writer`, `reader`). Garden-tagged facts are never replicated to federation peers — garden membership is node-local.

**Spec:** `Spec-02-Scopes-and-ACL`

```bash
curl -X POST http://localhost:8765/v1/gardens \
  -H "Authorization: Bearer $KEY" \
  -d '{"slug": "project-atlas", "name": "Project Atlas", "scope": "company"}'
```

---

## HLC (Hybrid Logical Clock) {#hlc}

The timestamp scheme used for causal ordering across federated nodes. Format: `{wall_ms_utc}.{counter}` (e.g., `1746230400000.003`). On each local write, the node advances the clock to `max(now_ms, last_hlc_ms)` and increments the counter if the wall component is unchanged. On receiving a federated fact, the clock advances to `max(now_ms, received_hlc_ms)`. HLCs ensure that causally related facts are correctly ordered even when wall clocks drift between nodes.

**Spec:** `Spec-12-HLC-Bounded-Skew`

```
1746230400000.003   ← wall_ms = 1746230400000, counter = 3
```

---

## Relation {#relation}

A namespaced string that identifies what kind of statement a fact makes about its entity. Relations use a `namespace:name` format (e.g., `memory:role`, `garden:member`, `roadmap:status`) to prevent collisions between independent systems asserting facts about the same entity. The spec maintains a namespace registry of reserved prefixes.

**Spec:** `Spec-01-Fact-Model`, `Spec-16-Namespace-Registry`

```
memory:role          ← the entity's role, in the memory namespace
garden:member        ← garden membership relation
stigmem:received_from ← system-generated provenance relation
```

---

## Scope {#scope}

One of four visibility levels that partition facts for access control and federation eligibility:

| Scope | Visibility | Federates? |
|-------|-----------|------------|
| `local` | Node-only, never leaves this instance | No |
| `team` | Logical team boundary, node-operator-defined | No |
| `company` | Owning company node | Only when PeerDeclaration explicitly allows |
| `public` | Any registered peer | Yes, by default |

Scope is enforced at write time (API key must permit the scope), read time (queries only return facts the caller's key allows), and federation time (outbound replication respects PeerDeclaration scope limits).

**Spec:** `Spec-02-Scopes-and-ACL`

---

## Source Attestation {#source-attestation}

The mechanism that binds a fact's declared `source` URI to the caller's authenticated `entity_uri` at write time. Without attestation, any authenticated principal could claim to be anyone by writing an arbitrary `source` value. The node enforces attestation in one of three modes: `enforce` (reject mismatches), `warn` (accept but flag with `attested: false`), or `off` (no check). Production multi-tenant deployments should use `enforce`.

**Spec:** `Spec-X6-Source-Attestation`, `Spec-02-Scopes-and-ACL`

```bash
# A key with entity_uri "stigmem://node/agent/bot-a" can only write
# facts with source matching that URI (in enforce mode)
curl -X POST http://localhost:8765/v1/facts \
  -H "Authorization: Bearer $BOT_A_KEY" \
  -d '{"entity": "stigmem://node/user/alice", "relation": "memory:role",
       "value": {"type": "string", "v": "engineer"},
       "source": "stigmem://node/agent/bot-a", "scope": "company"}'
```

---

## Tombstone {#tombstone}

A signed right-to-be-forgotten (RTBF) marker for retracted facts. Tombstones go beyond normal retraction (`confidence = 0.0`) by providing a cryptographically signed record with an expiry that instructs all receiving nodes to purge the target fact from storage, vector indexes, and caches. Tombstones are replicated via the federation tombstone route and are the primary mechanism for GDPR/RTBF compliance in federated deployments.

**Spec:** `Spec-X2-RTBF-Tombstones`
