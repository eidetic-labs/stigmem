# Spec-X2-RTBF-Tombstones — Status

> Per [ADR-008](../../docs/adr/008-experimental-gates.md), gate status for `experimental/tombstones/`. Spec ID per [ADR-010](../../docs/adr/010-modular-specs.md).

**Spec ID:** `Spec-X2-RTBF-Tombstones`
**Legacy section:** §23
**Status:** Dormant
**Active version:** v0.9.0a1 (code last functional under retracted v1.0)
**Last updated:** 2026-05-16
**Owner:** unowned
**Buildable:** yes

---

## Summary

§23 introduces tombstone records — signed admin-issued records that suppress facts for a given entity URI from all recall and query results. Tombstones serve "right to be forgotten" (RTBF) workflows for regulatory compliance: a data subject requests erasure, an operator issues a tombstone, the entity's facts disappear from all reads. A `legal_hold: true` flag preserves the underlying facts in time-travel queries (§24) for legitimate legal-preservation purposes while still hiding them from normal recall.

## Why deferred

Per ADR-002 and the threat-model risk register:

- **R-16 (Medium):** Admin key compromise enables tombstone DoS — irreversible suppression of any entity URI. Once a tombstone is issued, only a `TombstoneRevocation` (also admin-only) can lift it. There is no self-healing path; an attacker with an admin key can permanently disrupt agents that depend on facts for tombstoned entities.
- **R-17 (Medium):** `legal_hold: true` tombstones preserve historical data accessible via `as_of` queries (§24) to admin keys. After tombstone issuance, an admin key compromise leaks pre-tombstone history — meaning RTBF data subjects whose data was preserved under legal hold believe their data is erased, but it isn't from the perspective of an attacker holding admin credentials.
- **Tombstones interact with §24 time-travel and §25 CIDs** in ways that need integration test coverage that doesn't yet exist.
- **Operationally complex:** tombstone issuance is a regulatory-impact action. Operators need a runbook for review-before-issuance, audit trail expectations, revocation procedures, and federation propagation semantics. v1.0 didn't ship those operator artifacts.

---

## Gate progress

| Gate | Description | Status | Date | Artifact |
|---|---|---|---|---|
| 1 | Threat-model delta | Open | 2026-05-15 | [`security.md`](security.md) |
| 2 | ADR | Open | — | — |
| 3 | Conformance vectors | Open | — | — |
| 4 | 30-day external operator soak | Open | — | — |
| 5 | Documentation parity | Open | — | — |

---

## Notes per gate

### Gate 1 — Threat-model delta

The feature-owned security analysis now lives in [`security.md`](security.md)
per ADR-018. It records R-16 and R-17 as owned risks. The remaining delta work
needs to address:

- **Tombstone DoS recovery:** what's the operational procedure when a compromised admin key issued tombstones for critical entities? The current §23 spec has revocation but no operator runbook. The delta should specify required time-to-detect, time-to-revoke targets, and the fallback when the revocation key is also compromised.
- **Legal-hold scope:** R-17 implies a tighter scope on legal-hold than the original §23 design. Consider: should legal-hold `as_of` queries require a *separate* admin role (`legal_hold_reader`) distinct from general admin, so that a normal admin key compromise doesn't expose legal-hold history?
- **Federation propagation:** when an operator issues a tombstone, does it propagate to federation peers automatically? Original §23 says yes; the delta needs to consider whether this is correct (peers may have legitimate reasons to keep their copy) and what audit trail is left when peers refuse to accept.
- **Tombstone forgery:** R-16 covers the compromised-admin case. The delta should also cover an external attacker attempting to inject tombstone records via federation — the current §23 design relies on Ed25519 signatures, which the delta should explicitly model.

### Gate 2 — ADR

Open design questions that need ADR resolution:

1. Should tombstones require **two-admin sign-off** for entity URIs with more than N dependent agents? §8.2 of the threat model recommends this; needs a concrete spec.
2. Should `legal_hold: true` require a separate role or capability beyond standard admin?
3. What's the audit-event taxonomy for tombstones? The current threat model says `admin_action` event; the operator runbook will likely need finer granularity (`tombstone_issued`, `tombstone_revoked`, `legal_hold_issued`, `legal_hold_lifted`).

### Gate 3 — Conformance vectors

Required adversarial vectors:

- Tombstone with forged Ed25519 signature → expect 401.
- Tombstone issued by non-admin key → expect 403.
- Tombstone targeting an entity that's already tombstoned → expect 409 (idempotent rejection or update of revocation status).
- `as_of` query crossing a tombstone boundary by a non-admin key → expect tombstoned entity excluded.
- `as_of` query crossing a `legal_hold: true` boundary by an admin key → expect entity included with audit trail.
- Federation inbound tombstone from peer that lacks `tombstone:write` capability → expect rejection.
- Tombstone revocation issued by a different admin than the original tombstone → expect success (any admin can revoke).

### Gate 4 — Operator soak

Tombstone soak is **higher-stakes than typical features** — operators run RTBF workflows on real data. Two requirements unique to this feature:

1. **Soak operator must be a regulated-data deployment.** A toy-data soak doesn't surface the regulatory-workflow concerns. Candidates: SOC 2 in-scope deployments, GDPR-relevant teams, healthcare-adjacent agent platforms.
2. **Soak duration: 60 days minimum.** RTBF processes are slow; 30 days isn't enough to observe revocation, federation propagation, and legal-hold workflows in realistic operational rhythm.

### Gate 5 — Documentation parity

- **Learn:** explanation of RTBF workflow, what tombstones are and aren't.
- **Build:** API reference for `POST /v1/tombstones`, `POST /v1/tombstones/{id}/revoke`; SDK examples.
- **Operate:** **runbook for tombstone issuance** (the longest of the operator runbooks); audit-log queries for compliance reporting; recovery procedures for compromised-admin scenarios.
- **Secure:** scenarios 6.2, 7.1 (already drafted in scenarios.md additions); threat-model delta link; explicit warning that tombstones are irreversible suppression and admin key hygiene is critical.

---

## Open questions

1. **Should tombstones be supported in single-org deployments before the federation tombstone-propagation story is solved?** Recommend: yes. Single-org deployments cover the RTBF use case for many adopters; federation propagation is a follow-up. The reintroduction can be staged: §23-single-org as v1.1, §23-federation as v1.2.

2. **What happens when a tombstoned entity URI is later re-asserted with new facts?** Original §23 has the tombstone match by entity URI, so new facts are also suppressed. This may not be the intended behavior for an RTBF data subject who returns to the platform later. The reintroduction ADR needs to decide.

3. **Should the tombstone-revocation flow leave a public audit trail visible to data subjects?** Privacy laws often require operators to be able to demonstrate that erasure happened and was not silently reversed. Worth considering whether revocations need an external (Rekor-style) attestation.

---

## History

- **2026-05-16** — PR 4d #321 gated default-install tombstone behavior behind
  `stigmem-plugin-tombstones` registration. Default installs no longer mount
  tombstone admin/federation routes or apply legacy tombstone read filters;
  plugin-loaded tests preserve the historical behavior for alpha validation.
- **2026-05-16** — PR 4d scaffold added the
  `experimental/tombstones/` plugin source package with manifest, config
  schema, hook placeholders, plugin-owned tombstone migration declaration, and
  registration tests. Runtime extraction and default-install gating remain
  follow-on PR 4d work.
- **2026-05-15** — added ADR-018 colocated security analysis in `security.md`.
- **2026-05-06** — moved to `experimental/` per ADR-002. Status: Dormant.
- **2026-05-04** — `EXPERIMENTAL` caution banner added to §23 in spec (see commit `10c4ace`).
- **2026-05-03** — original §23 normative spec published in v2.0 (now retracted).
