# Stigmem Roadmap

> Public roadmap for stigmem. Phase-gated, not time-gated — phases complete when their exit criteria are met. Derived from `Internal-Comms/stigmem/plans/strengthening-plan.md` and `master-checklist.md`.
>
> **Current phase:** Phase A — Honesty Pass.
> **Current build:** v0.9.0a1 (first build; per [ADR-001](docs/adr/001-versioning.md) + [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md)).
> **Last updated:** 2026-05-09.

---

## Phase model

The work is organized into four sequential phases. Each phase has explicit entry and exit criteria. Sub-work within a phase can run in parallel.

| Phase | Goal | Build line |
|---|---|---|
| **A — Honesty Pass** | Public posture matches reality. v0.9.0a1 reset; cross-cutting features extracted to plugins per [ADR-011](docs/adr/011-cross-cutting-extraction.md); docs site restructured. | `v0.9.0a1` … `v0.9.0a8` |
| **B — Hardened Core** | Every Open risk in the v1.0 critical-path threat model closes. Capability redesign, federation hardening, Argon2id migration, OpenClaw safety, modular spec migration, storage immutability stack, 30-day external operator soak. | `v0.9.0b1` … `v0.9.0bN` |
| **C — v1.0.0 GA** | Sigstore-signed releases; reproducible builds; SBOM; 3+ external operators in production. Wire format frozen. | `v1.0.0rc1` … `v1.0.0` |
| **D — Expansion (post-v1.0)** | Experimental features graduate back to core via [ADR-008](docs/adr/008-experimental-gates.md) reintroduction gates; modular spec evolution. | `v1.x.y` |

---

## Phase A — Honesty Pass

**Status:** in progress.

### Phase A entry criteria
- [x] Pre-flight contributor decisions complete
- [x] [ADR-001](docs/adr/001-versioning.md), [ADR-002](docs/adr/002-v1-scope.md), [ADR-008](docs/adr/008-experimental-gates.md), [ADR-011](docs/adr/011-cross-cutting-extraction.md) accepted

### Phase A work
- [x] **PR 0** — Reset to v0.9.0a1 (technical work; published 2026-05-09)
- [ ] **PR 2** — Honesty pass on docs and ADRs (this PR)
- [ ] **PR 2.5** — Docs site restructure (per [ADR-005](docs/adr/005-docs-ia.md): four-tab IA — Learn / Build / Operate / Secure)
- [ ] **PR 3** — Cuts to `experimental/` (per [ADR-009](docs/adr/009-repo-structure.md))
- [ ] **PR 0.5** — Public retraction announcement (after docs are coherent)
- [ ] **PR 4 series** — Plugin infrastructure + seven cross-cutting plugins per ADR-011:
  - **PR 4-INF.1–4** — Hook registry + lifecycle + signing + testing infrastructure + plugin author docs
  - **v0.9.0a2** — `stigmem-plugin-lazy-instruction-discovery` (§21)
  - **v0.9.0a3** — Content-addressed fact IDs as core ([ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md); §25)
  - **v0.9.0a4** — `stigmem-plugin-time-travel` (§24)
  - **v0.9.0a5** — `stigmem-plugin-tombstones` (§23 RTBF)
  - **v0.9.0a6** — `stigmem-plugin-memory-garden-acl` (§17 advanced ACL)
  - **v0.9.0a7** — `stigmem-plugin-source-attestation` (§18)
  - **v0.9.0a8** — `stigmem-plugin-multi-tenant`

### Phase A exit criteria
- Public retraction visible.
- Repo top-level matches ADR-009 shape (~22 entries; `experimental/` is canonical home for deferred features).
- Plugin infrastructure shipped per ADR-011.
- All seven cross-cutting features implemented as plugins under `experimental/<feature>/`. Core has no feature-specific code.
- Default install (no plugins registered) produces v1.0 critical-path behavior.
- Multi-tenant adopters opt into `stigmem-plugin-multi-tenant`.
- All 19 ADRs committed to `docs/adr/`.
- Threat model and scenarios calibrated to v0.9.0a1 posture.
- `make demo` works on a clean machine.
- Per-hook firing benchmarks within budget (<10μs per hook).

---

## Phase B — Hardened Core (with Operator Validation)

**Status:** not started. Entry blocked on Phase A exit.

### Phase B work (sub-phase ordering matters)

1. **OpenClaw safety hardening (entry PR)** — closes Critical/High audit findings (C1–C4, H1–H5). See `adapters/openclaw/AUDIT.md`.
2. **Modular spec migration** per [ADR-010](docs/adr/010-modular-specs.md) — decompose `spec/stigmem-spec-v0.9.0a1.md` into 14 core specs with independent versioning.
3. **Capability redesign** per [ADR-003](docs/adr/003-prompt-injection.md) — `interpret_as` field on `FactValue`; default-deny on instruction interpretation; cross-org instruction quarantine; channel-separated `recall()` response.
4. **Adversarial conformance corpus** per [ADR-015](docs/adr/015-adversarial-conformance-and-model-certification.md) — 80+ patterns across 10 categories; multi-provider model certification framework.
5. **Storage immutability stack** per [ADR-016](docs/adr/016-storage-immutability-enforcement.md) — L1 architectural append-only journal + projection tables, L2 SQLite triggers, L3 CIDs (per [ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md)), L4 local hash chain, L5 Sigstore Rekor anchor, plus client/peer verification.
6. **Per-feature security colocation** per [ADR-018](docs/adr/018-security-documentation-colocation.md).
7. **Federation hardening** — mTLS-default; HLC bounded skew; persistent audit log (90-day retention); per-principal token-bucket quotas; key max-age + rotation runbook.
8. **Argon2id migration** per [ADR-007](docs/adr/007-argon2id.md) — dual-mode verification; opportunistic re-hash; benchmarks.
9. **Operator-facing documentation** — runbooks, observability signals per [ADR-004](docs/adr/004-federation-observability.md), prompt-injection hardening guide.
10. **30-day external operator soak** — at least one external operator runs against the hardened core with public bug reporting.

### Phase B exit criteria
- Threat-model risk register has no Open status entries for v1.0 critical-path risks.
- OpenClaw audit findings all show Closed status.
- 30-day external operator soak completes; all P0 findings addressed.
- v1.0.0-rc.0 ready to declare.

---

## Phase C — v1.0.0 GA

**Status:** not started. Entry blocked on Phase B exit + 14 days of v1.0.0-rc.N observation without critical regression.

### Phase C work
- Sigstore-signed releases (verifiable on every artifact).
- Reproducible builds (verified by an independent party).
- SBOM publication.
- 3+ external organizations running stigmem with pairwise federation.
- Public bug bounty operational.
- Wire-format freeze; backwards compatibility committed within v1.x.

### Phase C exit criteria
- v1.0.0 stable shipped.
- Wire format committed.
- Compatibility commitment doc per [ADR-013](docs/adr/013-deprecation-policy.md) honored across the v1.x line.

---

## Phase D — Expansion (post-v1.0)

**Status:** not started. Entry blocked on Phase C exit (v1.0.0 stable shipped).

### Phase D work
- Experimental features graduate back to core via [ADR-008](docs/adr/008-experimental-gates.md) reintroduction gates (each gate produces a concrete artifact: threat-model delta, ADR, conformance vectors, 30-day soak, documentation parity).
- Multi-tenant likely the highest-priority graduation candidate based on adopter demand.
- Modular spec evolution.
- Plugin ecosystem matures; third-party plugins become first-class.

### Phase D exit criteria
- None defined; this is the project's steady state.

---

## How to follow along

- **Public engineering log:** Friday weekly post in `docs/blog/` (Phase A onwards).
- **CHANGELOG.md** at repo root — Keep-a-Changelog format.
- **GitHub Project — "Stigmem GA Readiness Plan":** [Eidetic-Labs/projects/1](https://github.com/orgs/Eidetic-Labs/projects/1) (flips public at v0.9.0a1 retraction).
- **ADR index:** [`docs/adr/README.md`](docs/adr/README.md).
- **Compatibility matrix** (Phase B): published at `docs.stigmem.dev/operate/compatibility`.
- **Model certification list** (Phase B per ADR-015): published at `docs.stigmem.dev/secure/model-certification`.

---

## Stability commitments by phase

Per [ADR-001](docs/adr/001-versioning.md) + [ADR-013](docs/adr/013-deprecation-policy.md):

- **Pre-1.0 (`v0.9.0aN`, `v0.9.0bN`, `v1.0.0rcN`):** No stability guarantee. Breaking changes in any release; pin to specific versions; auto-upgrade is not safe.
- **`v1.0.0` and `v1.x`:** Wire format and public Python API are stable. Removing a public API requires a deprecation in v1.x followed by removal no earlier than v2.0.0.
- **Deprecated features:** supported through the rest of the major version they were deprecated in.
- **Experimental features:** subject to breaking changes in any release without notice; their use behind feature flags is at-your-own-risk.

---

*Roadmap is a living document. Updates land alongside ADR amendments and phase transitions. Contributions to roadmap shaping go through the ADR amendment process per [ADR-001](docs/adr/001-versioning.md) §Contributor approval rule.*
