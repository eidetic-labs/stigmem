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
- [x] **PR 2** — Honesty pass on docs and ADRs (#54, merged 2026-05-10)
- [x] **PR 2.5** — Docs site restructure (per [ADR-005](docs/adr/005-docs-ia.md): four-tab IA — Learn / Build / Operate / Secure) (#56 + #59 cross-link sweep, merged 2026-05-10)
- [x] **PR 3** — Cuts to `experimental/` (per [ADR-009](docs/adr/009-repo-structure.md)) (#60, merged 2026-05-10; spec-naming follow-ups in #61, #63)
- [ ] **PR 0.5** — Public retraction announcement (after docs are coherent; in flight, blocking on v0.9.0a1 PyPI/npm publish completion)
- [ ] **PR 4 series** — Plugin infrastructure + seven cross-cutting plugins per ADR-011:
  - **PR 4-INF.1–4** — Hook registry + lifecycle + signing + testing infrastructure + plugin author docs
  - **v0.9.0a2** — `Spec-X1-Lazy-Instruction-Discovery` graduates → `stigmem-plugin-lazy-instruction-discovery` ([§21 legacy])
  - **v0.9.0a3** — `Spec-X4-Content-Addressed-IDs` graduates **to core** ([ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md); [§25 legacy])
  - **v0.9.0a4** — `Spec-X3-Time-Travel` graduates → `stigmem-plugin-time-travel` ([§24 legacy])
  - **v0.9.0a5** — `Spec-X2-RTBF-Tombstones` graduates → `stigmem-plugin-tombstones` ([§23 legacy])
  - **v0.9.0a6** — `Spec-X5-Memory-Garden` graduates → `stigmem-plugin-memory-garden-acl` ([§17 advanced legacy])
  - **v0.9.0a7** — `Spec-X6-Source-Attestation` graduates → `stigmem-plugin-source-attestation` ([§18 legacy])
  - **v0.9.0a8** — Multi-tenant graduates → `stigmem-plugin-multi-tenant` (cross-cutting; no §N legacy)

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

## Spec naming convention

Per [ADR-010](docs/adr/010-modular-specs.md): the canonical spec naming is **`Spec-NN-Topic-Name`** (or **`Spec-XN-Topic-Name`** for experimental specs), with stable two-digit identifiers and descriptive names.

| Prefix | Meaning | Example |
|---|---|---|
| `Spec-NN-` | Core spec; in-tree at `spec/specs/NN-topic-name.md` once the modular migration lands | `Spec-01-Core`, `Spec-09-Audit-Log` |
| `Spec-XN-` | Experimental spec; lives at `experimental/<feature>/spec.md` per [ADR-009](docs/adr/009-repo-structure.md) §2 | `Spec-X1-Lazy-Instruction-Discovery` |

**The number is stable across renames.** If a spec's topic name changes, the number stays. New specs get the next available number; numbers are never reused.

### Why the legacy `§N` numbering is still visible

The pre-reset stigmem spec was a single monolithic document with sections numbered §1 through §25. ADR-010 supersedes that model — but the **full per-spec decomposition is Phase B work** per master-checklist §5.1 and ADR-010's own implementation plan. Until Phase B ships:

- The canonical spec stays as a single file at `spec/stigmem-spec-v0.9.0a1.md`.
- Cross-references in this ROADMAP use `Spec-XN-Name` as the **primary** identifier with `[§N legacy]` as a transitional aid for readers familiar with the pre-reset numbering.
- Each `experimental/<feature>/STATUS.md` declares its `spec_id: Spec-XN-Topic-Name` in frontmatter.
- Per-section file decomposition (`spec/specs/01-core.md` through `spec/specs/14-batch-assert.md`, plus the `spec/PROTOCOL.md` meta-document) lands in Phase B.

### Spec ID inventory

**Core specs (Phase B target — 14 files):**

| Spec ID | Topic | Maps from legacy §§ |
|---|---|---|
| `Spec-01-Core` | Core data model | §1–§5 |
| `Spec-02-Scopes-and-ACL` | Scopes + basic ACL | §3.5, §17 (basic ACL only) |
| `Spec-03-API` | HTTP API contract | API surface across §§ |
| `Spec-04-Manifests` | Manifests + Rekor | §19.1–§19.2 |
| `Spec-05-Federation-Trust` | Federation trust (peer auth, replication) | §19 |
| `Spec-06-Capability-Tokens` | Capability tokens | §19.3 |
| `Spec-07-Recall-Pipeline` | Recall pipeline (basic) | §6, §20 (basic) |
| `Spec-08-Quarantine-Garden` | Quarantine semantics | §19.5 |
| `Spec-09-Audit-Log` | Audit log | §22.3 |
| `Spec-10-Hardening` | Security hardening | §22.1, §22.2, §22.4, §22.6 |
| `Spec-11-Replay-Protection` | Replay protection | §22.5 |
| `Spec-12-HLC-Bounded-Skew` | HLC bounded skew | (new; per R-19) |
| `Spec-13-Capability-Based-Instructions` | `interpret_as` capability model | (new; per ADR-003) |
| `Spec-14-Batch-Assert` | Batch fact assert | (new; per ADR-006) |

**Experimental specs (currently at `experimental/<feature>/spec.md`):**

| Spec ID | Topic | Located at | Maps from legacy § |
|---|---|---|---|
| `Spec-X1-Lazy-Instruction-Discovery` | Lazy instruction discovery | `experimental/lazy-instruction-discovery/spec.md` | §21 |
| `Spec-X2-RTBF-Tombstones` | RTBF tombstones | `experimental/tombstones/spec.md` | §23 |
| `Spec-X3-Time-Travel` | `as_of` time-travel queries | `experimental/time-travel/spec.md` | §24 |
| `Spec-X4-Content-Addressed-IDs` | CIDs (graduates **to core** at v0.9.0a3 per [ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md)) | `experimental/cids/spec.md` until graduation | §25 |
| `Spec-X5-Memory-Garden` | Memory garden advanced ACL | `experimental/memory-garden-acl/spec.md` | §17 advanced |
| `Spec-X6-Source-Attestation` | Source attestation | `experimental/source-attestation/spec.md` | §18 |
| `Spec-X7-Subscriptions` | Subscriptions / push federation | `experimental/subscriptions/spec.md` | (new) |

---

## Spec graduation process

When does a spec move from `Spec-X*` (experimental) to `Spec-NN` (core)?

Per [ADR-008](docs/adr/008-experimental-gates.md): **all five gates pass.** Each gate produces a concrete artifact; only after the founder (or two contributors per ADR-001 §Contributor approval rule) signs off on all five does the feature graduate.

### The five gates

| # | Gate | Artifact |
|---|---|---|
| 1 | Threat-model delta | `experimental/<feature>/security.md` per ADR-018, merged into `spec/security/threat-model.md` |
| 2 | ADR drafted and merged | `docs/adr/NNN-<feature>.md` |
| 3 | Conformance vectors | `data/conformance/<feature>/` including adversarial cases |
| 4 | 30-day external operator soak | LOG.md entry in this repo with at least one closed issue tagged `<feature>-soak-finding` |
| 5 | Documentation parity | Pages across all four tabs (Learn / Build / Operate / Secure) per [ADR-005](docs/adr/005-docs-ia.md) |

Order matters per ADR-008: 1 before 2, 3 before 4, 5 last. Skipping requires explicit two-contributor sign-off recorded in the feature's ADR.

### What changes when a spec graduates (worked example)

Using `Spec-X1-Lazy-Instruction-Discovery` graduating at v0.9.0a2 as the worked case:

| Surface | Before graduation (v0.9.0a1) | After graduation (v0.9.0a2) |
|---|---|---|
| Spec content | `experimental/lazy-instruction-discovery/spec.md` (Spec-X1) | Migrated into core spec under a new `Spec-NN-Lazy-Instruction-Discovery` ID once Phase B's modular spec migration lands; until then, content moves into the canonical `spec/stigmem-spec-v0.9.0aN.md` |
| Plugin package | Not published | `stigmem-plugin-lazy-instruction-discovery` published to PyPI |
| Default install behavior | Routes mounted but feature dormant unless configured (per LIMITATIONS §11) | Plugin is opt-in; default install is unchanged in user-visible behavior. Operators who want the feature install the plugin |
| `experimental/<feature>/STATUS.md` | `Status: Dormant`, all 5 gates Open | `Status: Graduated`, all 5 gates Done with dates |
| `Internal-Comms/stigmem/plans/version-prioritization.md` | Listed in DEFER section | Listed in graduated section with the release tag and gate-completion dates |
| `ROADMAP.md` Phase A table | This row | ✅ Done; deleted from the in-flight table; called out in the changelog |
| `concepts/features.md` | `stability: experimental` | `stability: stable` (or `beta` if the feature ships behind a flag) |
| `docs/compatibility-matrix.yaml` | `stability: experimental` for the feature | Updated stability tier + concrete version requirements |
| `CHANGELOG.md` | — | Entry under `### Added` for v0.9.0a2 noting the graduation, the gate evidence, and the migration notes for adopters |
| `spec/EVOLUTION.md` | — | Entry recording the protocol-release-level spec change (Spec-X1 → graduated; new spec-set composition for v0.9.0a2) |
| `data/conformance/lazy-instruction-discovery/` | empty | Adversarial + behavioral vectors required by Gate 3 |

### What does NOT happen automatically

- The feature does **not** become default-on. Plugin architecture per [ADR-011](docs/adr/011-cross-cutting-extraction.md) means graduated cross-cutting features are shipped as opt-in plugins. "Graduated" means the feature passed quality bars, not that every adopter gets it.
- The legacy `§N` reference is **not** silently removed from older docs. Cross-references in archived snapshots at `spec/archive/evolution/` continue to use the original numbering for historical accuracy.
- Older releases are **not** retroactively updated. v0.9.0a1 remains a published, immutable release; the graduation lands in v0.9.0a2's release artifacts.

### What the founder reviews at graduation

A graduation PR should include:
1. The five gate artifacts above
2. The ROADMAP.md row update (this row → ✅ Done)
3. The CHANGELOG entry under `### Added` for the graduating release
4. The `experimental/<feature>/STATUS.md` flip from Dormant → Graduated with all five gate dates
5. The `concepts/features.md` row update
6. The `compatibility-matrix.yaml` update

CI rejects a graduation PR that's missing any of those artifacts (per ADR-013 deprecation-policy validator pattern + ADR-008 gate-tracking).

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
