---
id: scope-propagation
title: Scope Propagation Invariants
sidebar_label: Scope Propagation
---

# Scope Propagation Invariants

:::info v0.8 — Normative
Scope propagation invariants are **normative** in spec v0.8 (§6.8). These close the open question in §8.5 of v0.7 regarding `company`-scoped fact re-federation. All nodes running v0.8 or later MUST implement invariant 6.8.1 and 6.8.2.
:::

**Audience:** Node operators and federation architects building multi-hop topologies where facts cross organizational boundaries.

## The core principle: scope cannot escalate at relay hops

A fact's scope is an authorization grant, not a label. When a `team`-scoped fact enters node B from node A, it means "A permits B to see this fact as a team fact." Node B cannot widen that grant — it cannot re-federate the fact to node C as if C had the same authorization A gave to B.

**Invariant 6.8.1 (Transitive Scope Non-Escalation):** A fact's scope MUST NOT be escalated at any relay hop. Each relay node intersects the fact's scope against its own PeerDeclaration `allowed_scopes` before including the fact in a pull response. The narrower scope wins.

## How scope propagation works in practice

When node B ingests a federated fact from node A, it records two internal metadata fields (never re-replicated):

| Field | Description |
|---|---|
| `origin_node_id` | The node that originally asserted the fact |
| `origin_allowed_scopes` | The scope grant A's PeerDeclaration extended to B |

When C later pulls from B, B intersects:

```
fact.scope ∩ origin_allowed_scopes ∩ C's PeerDeclaration allowed_scopes
```

If the intersection is empty (e.g., A granted B `team` scope but C's PeerDeclaration only has `local`), the fact is excluded from B's pull response to C — not an error, just a scope filter.

## Company-scoped facts: no re-federation (§6.8.2)

This invariant resolves v0.7 §8.5 directly.

**Invariant 6.8.2:** A node that receives a `company`-scoped fact MUST NOT re-federate it to any third node, regardless of the third node's PeerDeclaration.

**Why:** `company` scope is an authorization grant to a specific peer (node B), not to B's entire downstream network. If node A shares a company fact with B, A is trusting B — not B's federation partners.

Implementation: ingested company-scoped facts are tagged `re_federation_blocked=true` at ingest time. These facts are excluded from all outgoing federation pull responses.

**Exception:** Set `STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=true` to lift this restriction. Use with care — this must be agreed bilaterally with the origin node, and all re-federation events are written to the federation audit log.

```bash
# Only enable if origin node has explicitly consented
STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION=false  # default; recommended
```

## Edge cases (§6.8.3)

### Mixed-scope batches

When a push batch contains facts with different scopes, scope violations on individual facts do not reject the entire batch. Each fact is evaluated independently. Violating facts are rejected (HTTP 403 per-fact, `event_type="scope_violation"` in audit log); valid facts in the batch proceed normally.

### Scope of contradiction meta-facts

`stigmem:conflict:between` meta-facts inherit the scope of the conflicting source facts. When two facts with different scopes conflict, the narrower scope wins:

| Fact A scope | Fact B scope | Conflict meta-fact scope |
|---|---|---|
| `company` | `team` | `team` |
| `public` | `local` | `local` |
| `team` | `team` | `team` |

This prevents contradiction meta-facts from escalating scope beyond what the narrower source fact permitted.

### Out-of-scope fact from peer

If a peer pushes a `team`-scoped fact but the receiving node's PeerDeclaration for that peer does not include `"team"` in `allowed_scopes`:

1. Node returns HTTP 403 on the specific fact
2. `event_type="scope_violation"` is written to the federation audit log
3. The PeerDeclaration is authoritative — local environment flags cannot override it

**Important:** `STIGMEM_FEDERATION_ALLOW_COMPANY_REFEDERATION` controls re-federation policy, not what scopes a peer is permitted to send. Peer scope grants are in the PeerDeclaration, not environment flags.

## Audit log entries

Scope violations produce structured entries in the federation audit log:

```json
{
  "event_type": "scope_violation",
  "fact_id": "...",
  "peer_id": "node-b-peer-id",
  "claimed_scope": "team",
  "allowed_scopes": ["local"],
  "timestamp": "2026-05-02T18:10:00Z"
}
```

Monitor these entries to detect misconfigured PeerDeclarations before they cause silent data loss.

## Invariant summary

| Invariant | Requirement | Default |
|---|---|---|
| 6.8.1 — Transitive scope non-escalation | MUST: intersect scopes at each relay hop | Always enforced |
| 6.8.2 — Company re-federation restriction | MUST: block re-federation of company-scoped facts | Enforced; opt-out via env var |
| 6.8.3 — Mixed-scope batches | MUST: per-fact evaluation, not all-or-nothing | Always enforced |
| 6.8.3 — Conflict meta-fact scope | MUST: inherit narrower scope of conflicting facts | Always enforced |

## See also

- [Federation guide](/docs/guides/federation) — PeerDeclaration registration and pull protocol
- [Relay backpressure guide](/docs/guides/relay-backpressure) — lag signals in N-node topologies
- Spec §6.8 — Scope Propagation Invariants
- Spec §6 — Federation protocol
- Spec §8.5 (v0.7) — Open question resolved by §6.8.2
