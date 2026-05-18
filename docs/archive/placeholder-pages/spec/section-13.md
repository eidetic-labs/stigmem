---
title: §13. Section 13
sidebar_label: §13 Section 13
audience: Spec
description: "Stigmem spec section 13 — "
---

# §13. Section 13 {#section-13}

**Status:** Unknown



**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

The following Phase 5 deliverables are addressed in v0.7 (complete):

- **Lint primitive** (Phase 5 Deliverable 3): §14 Lint Semantics normative. Done.
- **Entity normalization layer** (Phase 5 Deliverable 4): §2.6 Entity Naming Rules normative; strict normalizer on ingest path implemented (`entity_normalizer.py`); migration 003 (entity_aliases). Done.
- **Bug fixes**: §resolution-semantics (Deliverable 1) and §query-semantics (Deliverable 2) complete.

Phase 6 deliverables addressed in v0.8 (draft):

- **4-node federation backpressure + scope propagation** (Phase 6 D1 findings): §6.7–§6.8 draft normative sections. Pending D1 correctness test validation before stable promotion.
- **Decay semantics** (Phase 6 D4): §15 Decay Semantics draft. `POST /v1/decay/sweep` route; `DecayPolicy` registry; `decay_scope` MCP tool. Pending D4 implementation.
- **Synthesis** (Phase 6 D4): §16 Synthesis draft. `POST /v1/synthesis` route; `synthesize_scope` MCP tool. Pending D4 implementation.
- **Schema migration 004**: `origin_node_id`, `origin_allowed_scopes`, `re_federation_blocked` columns for scope-propagation tracking. Pending D1 validation.

The following are deferred to Phase 7+:

- Multi-tenant RBAC / OIDC
- Binary wire encoding
- Full `IntentEnvelope` wire route (§4 remains spec-only; Phase 7 target)
- Entity URI migration tooling (auto-rewrite from informal to formal URIs)
- Hosted public Stigmem node
- Async lint job API (`GET /v1/lint/jobs/:job_id`)
- Async decay sweep API (large scope; follows lint async pattern)
- Fuzzy entity resolver (Kompl-style 3-layer)
- Conflict resolution policy plugins
- Audit log retention policy

---
