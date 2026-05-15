# Stigmem Roadmap

> Public roadmap for stigmem. Milestone-gated, not time-gated — version lines complete when their exit criteria are met.
>
> **Current build:** v0.9.0a1 (first build; per [ADR-001](docs/adr/001-versioning.md) + [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md)).
> **Last updated:** 2026-05-13.

---

## Version-line model

The work is organized into four sequential version lines per [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). Each line has explicit entry and exit criteria. Sub-work within a line can run in parallel.

| Version line | Goal |
|---|---|
| **`v0.9.0aN` — alpha series** | Public posture matches reality. v0.9.0a1 reset; a2+ artifact refreshes correct ClawHub/OpenClaw alpha framing; cross-cutting features extracted to plugins per [ADR-011](docs/adr/011-cross-cutting-extraction.md); docs site restructured. |
| **`v0.9.0bN` — beta series (hardened core)** | Every Open risk in the v1.0.0 critical-path threat model closes. Capability redesign, federation hardening, Argon2id migration, OpenClaw safety, modular spec migration, storage immutability stack, 30-day external operator soak. |
| **`v1.0.0rcN` → `v1.0.0` — release candidates and GA** | Sigstore-signed releases; reproducible builds; SBOM; 3+ external operators in production. Wire format frozen. |
| **`v1.x.y` — post-GA expansion** | Experimental features graduate into the supported surface via [ADR-008](docs/adr/008-experimental-gates.md) reintroduction gates; cross-cutting features remain opt-in plugins per ADR-011; modular spec evolution. |

---

## `v0.9.0aN` — alpha series

**Status:** in progress.

### Entry criteria
- [x] Pre-flight contributor decisions complete
- [x] [ADR-001](docs/adr/001-versioning.md), [ADR-002](docs/adr/002-v1-scope.md), [ADR-008](docs/adr/008-experimental-gates.md), [ADR-011](docs/adr/011-cross-cutting-extraction.md) accepted

### Work
- [x] **Version reset and first public artifacts** — v0.9.0a1 published as the first build; earlier version markers reclassified as internal development checkpoints.
- [x] **Public retraction and posture calibration** — retraction post is live; README, SECURITY, LIMITATIONS, roadmap, and docs site now describe the alpha posture instead of the withdrawn v1.0 claim.
- [x] **Docs information architecture** — docs site follows ADR-005's Learn / Build / Operate / Secure structure.
- [x] **Deferred-feature layout** — out-of-scope features live under `experimental/` per ADR-009; CIDs remain core per ADR-017.
- [x] **Hook registry foundation** — main now includes the stable 22-hook registry surface, typed voting/filter-chain/score-delta/fire-and-forget semantics, deterministic manual/core registration, minimum `PluginManifest` / `PluginContext` / capability APIs, hook-site wiring across assertion/recall/federation/auth/migration/audit paths, registry audit/metrics plumbing, test registry helpers, and the hook-firing benchmark gate. This work landed after the v0.9.0a1 artifacts and is queued for the next alpha artifact refresh.
- [x] **Plugin infrastructure operationalization** — package discovery, plugin dependency lifecycle, health polling, operator CLI, production signing/trust, plugin author/operator documentation, and plugin migration lifecycle/checksum tracking have landed on `main` after v0.9.0a1 and are queued for the next alpha artifact refresh.
- [ ] **Per-feature plugin extraction** — lazy instruction discovery, time-travel, tombstones, memory-garden advanced ACL, source attestation, and multi-tenant isolation are extracted into opt-in experimental plugin packages across the alpha series. CIDs remain core.
- [ ] **v0.9.0a2 artifact refresh** — pick up the live retraction URL in packaged READMEs, TypeScript SDK README, npm dist-tag convention, ClawHub naming/versioning notes, GHCR tag policy, Python SDK version literal, wheel migration packaging fix, and ongoing lint/coverage/complexity ratchets.
- [ ] **ClawHub/OpenClaw alpha-framing correction** — ship in the v0.9.0a2 refresh, not as a retroactive a1 edit. ClawHub and OpenClaw docs must say the connector is available for alpha evaluation only, remove “recommended production integration” language, correct stale dependency ranges, and link to the open audit limitations.
- [ ] **OpenClaw audit planning for a2..aN** — keep the audit findings visible in alpha planning. Use a2 for public framing/docs corrections and issue decomposition; schedule adapter hardening work across the remaining alpha/beta path without claiming the a1 ClawHub package closed C1-C4 or H1/H2/H5.

### Exit criteria
- Public retraction visible.
- Repo top-level matches ADR-009 shape (~22 entries; `experimental/` is canonical home for deferred features).
- Hook registry foundation shipped, and remaining plugin infrastructure operationalized per ADR-011: package discovery/lifecycle, dependency resolution, health polling, operator CLI, production signing/trust, author/operator docs, and plugin migration lifecycle tracking.
- All six cross-cutting features implemented as plugins under `experimental/<feature>/`; CIDs remain core per ADR-017. Core has no remaining feature-specific code for deferred plugin features.
- Default install (no plugins registered) produces v1.0.0-critical-path behavior.
- Multi-tenant adopters opt into `stigmem-plugin-multi-tenant`.
- All 19 ADRs committed to `docs/adr/`.
- Threat model and scenarios calibrated to v0.9.0a1 posture.
- `make demo` works on a clean machine.
- Per-hook firing benchmarks within budget (<10μs per hook).

---

## `v0.9.0bN` — beta series (hardened core, with operator validation)

**Status:** not started. Entry blocked on the alpha series exit.

### Work (sub-work ordering matters)

1. **OpenClaw safety hardening (entry PR)** — closes Critical/High audit findings (C1–C4, H1–H5). See `adapters/openclaw/AUDIT.md`.
2. **Modular spec migration** per [ADR-010](docs/adr/010-modular-specs.md) — decompose `spec/stigmem-spec-v0.9.0a1.md` into component specs with independent versioning.
3. **Capability redesign** per [ADR-003](docs/adr/003-prompt-injection.md) — `interpret_as` field on `FactValue`; default-deny on instruction interpretation; cross-org instruction quarantine; channel-separated `recall()` response.
4. **Adversarial conformance corpus** per [ADR-015](docs/adr/015-adversarial-conformance-and-model-certification.md) — 80+ patterns across 10 categories; multi-provider model certification framework.
5. **Storage immutability stack** per [ADR-016](docs/adr/016-storage-immutability-enforcement.md) — L1 architectural append-only journal + projection tables, L2 SQLite triggers, L3 CIDs (per [ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md)), L4 local hash chain, L5 Sigstore Rekor anchor, plus client/peer verification.
6. **Per-feature security colocation** per [ADR-018](docs/adr/018-security-documentation-colocation.md).
7. **Federation hardening** — mTLS-default; HLC bounded skew; persistent audit log (90-day retention); per-principal token-bucket quotas; key max-age + rotation runbook.
8. **Argon2id migration** per [ADR-007](docs/adr/007-argon2id.md) — dual-mode verification; opportunistic re-hash; benchmarks.
9. **Operator-facing documentation** — runbooks, observability signals per [ADR-004](docs/adr/004-federation-observability.md), prompt-injection hardening guide.
10. **30-day external operator soak** — at least one external operator runs against the hardened core with public bug reporting.

### Exit criteria
- Threat-model risk register has no Open status entries for v1.0.0-critical-path risks.
- OpenClaw audit findings all show Closed status.
- 30-day external operator soak completes; all P0 findings addressed.
- v1.0.0rc1 ready to declare.

---

## `v1.0.0rcN` → `v1.0.0` — release candidates and GA

**Status:** not started. Entry blocked on the beta-series exit + 14 days of v1.0.0rcN observation without critical regression.

### Work
- Sigstore-signed releases (verifiable on every artifact).
- Reproducible builds (verified by an independent party).
- SBOM publication.
- 3+ external organizations running stigmem with pairwise federation.
- Public bug bounty operational.
- Wire-format freeze; backwards compatibility committed within v1.x.

### Exit criteria
- v1.0.0 stable shipped.
- Wire format committed.
- Compatibility commitment doc per [ADR-013](docs/adr/013-deprecation-policy.md) honored across the v1.x line.

---

## `v1.x.y` — post-GA expansion

**Status:** not started. Entry blocked on v1.0.0 GA shipping.

### Work
- Experimental features graduate into the supported surface via [ADR-008](docs/adr/008-experimental-gates.md) reintroduction gates (each gate produces a concrete artifact: threat-model delta, ADR, conformance vectors, 30-day soak, documentation parity). Cross-cutting features remain opt-in plugins per ADR-011 unless a future ADR explicitly changes that boundary.
- Multi-tenant remains a plugin (`stigmem-plugin-multi-tenant`); the cross-cutting plugin shape per ADR-011 is the permanent home, not a stop on the path to core. Adopters who need multi-tenancy install the plugin explicitly.
- Modular spec evolution.
- Plugin ecosystem matures; third-party plugins become first-class.

### Exit criteria
- None defined; this is the project's steady state.

---

## Spec naming convention

Per [ADR-010](docs/adr/010-modular-specs.md): the canonical spec naming is **`Spec-NN-Topic-Name`** (or **`Spec-XN-Topic-Name`** for experimental specs), with stable two-digit identifiers and descriptive names.

| Prefix | Meaning | Example |
|---|---|---|
| `Spec-NN-` | Supported protocol component spec; in-tree at `spec/specs/NN-topic-name.md` | `Spec-01-Fact-Model`, `Spec-09-Audit-Log` |
| `Spec-XN-` | Experimental spec; lives at `experimental/<feature>/spec.md` per ADR-009's experimental-feature layout | `Spec-X1-Lazy-Instruction-Discovery` |

**The number is stable across renames.** If a spec's topic name changes, the number stays. New specs get the next available number; numbers are never reused.

### Why Legacy Section Numbering Is Still Visible

The pre-reset stigmem spec was a single monolithic document with sections
numbered 1 through 25. ADR-010 supersedes that model. The supported component
specs now live under `spec/specs/`, experimental specs live under
`experimental/<feature>/spec.md`, and `spec/PROTOCOL.md` is generated from
their frontmatter.

### Spec ID inventory

**Supported protocol component specs:**

| Spec ID | Topic | Legacy source material |
|---|---|---|
| `Spec-01-Fact-Model` | Atomic fact model | Legacy section 2 |
| `Spec-02-Scopes-and-ACL` | Scopes + basic ACL | Legacy sections 3.5 and 17 basic ACL material |
| `Spec-03-HTTP-API` | HTTP API contract | Legacy API-surface material |
| `Spec-04-Manifests` | Manifests + Rekor | Legacy sections 19.1 and 19.2 |
| `Spec-05-Federation-Trust` | Federation trust (peer auth, replication) | Legacy section 19 |
| `Spec-06-Capability-Tokens` | Capability tokens | Legacy section 19.3 |
| `Spec-07-Recall-Pipeline` | Recall pipeline (basic) | Legacy sections 6 and 20 basic recall material |
| `Spec-08-Quarantine-Garden` | Quarantine semantics | Legacy section 19.5 |
| `Spec-09-Audit-Log` | Audit log | Legacy section 22.3 |
| `Spec-10-Hardening` | Security hardening | Legacy sections 22.1, 22.2, 22.4, and 22.6 |
| `Spec-11-Replay-Protection` | Replay protection | Legacy section 22.5 |
| `Spec-12-HLC-Bounded-Skew` | HLC bounded skew | (new; per R-19) |
| `Spec-13-Capability-Based-Instructions` | `interpret_as` capability model | (new; per ADR-003) |
| `Spec-14-Batch-Assert` | Batch fact assert | (new; per ADR-006) |
| `Spec-15-Fact-Semantics` | Fact semantics | Legacy section 3 |
| `Spec-16-Namespace-Registry` | Namespace registry | Legacy section 9 |
| `Spec-17-Schema-and-Migration` | Schema and migrations | Legacy section 10 |
| `Spec-18-Conformance-and-Failure-Modes` | Conformance and failure modes | Legacy section 11 |
| `Spec-19-Adapter-ABI` | Adapter ABI | Legacy section 12 |
| `Spec-20-Lint-Semantics` | Lint semantics | Legacy section 14 |
| `Spec-21-Content-Addressed-IDs` | Content-addressed IDs | Legacy section 25 |

**Experimental specs (currently at `experimental/<feature>/spec.md`):**

| Spec ID | Topic | Located at | Legacy source material |
|---|---|---|---|
| `Spec-X1-Lazy-Instruction-Discovery` | Lazy instruction discovery | `experimental/lazy-instruction-discovery/spec.md` | Legacy section 21 |
| `Spec-X2-RTBF-Tombstones` | RTBF tombstones | `experimental/tombstones/spec.md` | Legacy section 23 |
| `Spec-X3-Time-Travel-Queries` | `as_of` time-travel queries | `experimental/time-travel/spec.md` | Legacy section 24 |
| `Spec-X5-Memory-Garden-Advanced-ACL` | Memory garden advanced ACL | `experimental/memory-garden-acl/spec.md` | Legacy section 17 advanced material |
| `Spec-X6-Source-Attestation` | Source attestation | `experimental/source-attestation/spec.md` | Legacy section 18 |
| `Spec-X7-Subscriptions` | Subscriptions / push federation | `experimental/subscriptions/spec.md` | (new) |
| `Spec-X8-Intent-Envelope` | Intent envelope | `experimental/intent-envelope/spec.md` | Legacy section 4 |
| `Spec-X9-Decay-Semantics` | Decay semantics | `experimental/decay/spec.md` | Legacy section 15 |
| `Spec-X10-Synthesis` | Synthesis | `experimental/synthesis/spec.md` | Legacy section 16 |
| `Spec-X11-Recall-Graph` | Advanced recall graph | `experimental/recall-graph/spec.md` | Legacy section 20 advanced material |

---

## Experimental extraction vs. graduation

The alpha series and ADR-008 describe two different moves:

- **Alpha extraction (`v0.9.0aN`)** moves feature-specific code and spec text out of core and into opt-in experimental plugin packages. This preserves the v1.0.0 default-install scope while making the experimental feature easier to test. It does **not** make the feature supported, stable, or default-on.
- **ADR-008 graduation (`v1.x.y`, post-GA)** promotes an experimental feature into the supported surface after the five reintroduction gates pass. For cross-cutting features, the plugin remains a plugin; graduation changes its support/trust tier, not its architectural home.

### Alpha extraction process

During the alpha series, a feature can be extracted into an opt-in experimental plugin when the extraction preserves default-install behavior and the package is clearly marked as experimental.

Required extraction artifacts:

| Artifact | Purpose |
|---|---|
| Plugin package | `stigmem-plugin-<feature>` package with manifest, hook registrations, and tests |
| Spec placement | `experimental/<feature>/spec.md` remains the authoritative experimental spec text |
| Status file | `experimental/<feature>/STATUS.md` records extraction status, known gaps, and ADR-008 gate status |
| Compatibility note | Docs state that the plugin is opt-in, experimental, and not part of the stable/default surface |
| Changelog entry | Records the extraction and any migration instructions for existing alpha users |

Extraction should include targeted tests for the plugin boundary and default-install no-op behavior. It does not require the ADR-008 30-day soak.

### ADR-008 graduation process

When does a spec move from `Spec-X*` (experimental) toward `Spec-NN` (supported/core spec)?

Per [ADR-008](docs/adr/008-experimental-gates.md): **all five gates pass.** Each gate produces a concrete artifact; only after the founder (or two contributors per ADR-001 §Contributor approval rule) signs off on all five does the feature graduate into the supported surface.

### The five gates

| # | Gate | Artifact |
|---|---|---|
| 1 | Threat-model delta | `experimental/<feature>/security.md` per ADR-018, merged into `spec/security/threat-model.md` |
| 2 | ADR drafted and merged | `docs/adr/NNN-<feature>.md` |
| 3 | Conformance vectors | `data/conformance/<feature>/` including adversarial cases |
| 4 | 30-day external operator soak | LOG.md entry in this repo with at least one closed issue tagged `<feature>-soak-finding` |
| 5 | Documentation parity | Pages across all four tabs (Learn / Build / Operate / Secure) per [ADR-005](docs/adr/005-docs-ia.md) |

Order matters per ADR-008: 1 before 2, 3 before 4, 5 last. Skipping requires explicit two-contributor sign-off recorded in the feature's ADR.

### What changes during alpha extraction (worked example)

Using `Spec-X1-Lazy-Instruction-Discovery` being extracted at v0.9.0a2 as the worked case:

| Surface | Before extraction (v0.9.0a1) | After extraction (v0.9.0a2) |
|---|---|---|
| Spec content | `experimental/lazy-instruction-discovery/spec.md` (Spec-X1) | Remains experimental under `experimental/lazy-instruction-discovery/spec.md` until a future ADR-008 graduation |
| Plugin package | Not published | `stigmem-plugin-lazy-instruction-discovery` published to PyPI |
| Default install behavior | Routes mounted but feature dormant unless configured (per LIMITATIONS §11) | Plugin is opt-in; default install is unchanged in user-visible behavior. Operators who want the feature install the plugin |
| `experimental/<feature>/STATUS.md` | `Status: Dormant`, ADR-008 gates Open | `Status: Extracted / opt-in experimental`, ADR-008 gates still Open unless separately completed |
| `ROADMAP.md` v0.9.0aN work table | This row | ✅ Done; deleted from the in-flight table; called out in the changelog |
| `concepts/features.md` | Experimental; embedded/dormant implementation acknowledged | Experimental; opt-in plugin package available |
| `docs/compatibility-matrix.yaml` | `stability: experimental` for the feature | Still `stability: experimental`; version requirements point at the plugin package |
| `CHANGELOG.md` | — | Entry under `### Added` for v0.9.0a2 noting the extraction and migration notes for alpha users |
| `spec/EVOLUTION.md` | — | Entry recording the alpha extraction while preserving `Spec-X1` status |
| `data/conformance/lazy-instruction-discovery/` | optional/empty | Targeted plugin-boundary tests; full ADR-008 conformance vectors arrive before graduation |

### What does NOT happen during alpha extraction

- The feature does **not** become default-on. Plugin architecture per [ADR-011](docs/adr/011-cross-cutting-extraction.md) means extracted cross-cutting features are shipped as opt-in plugins.
- The feature does **not** become supported or stable. Stability remains experimental until ADR-008 gates pass.
- The feature does **not** move from `Spec-X*` to `Spec-NN`. That is a later graduation step.
- The ADR-008 five-gate process is **not** bypassed; it is simply not the alpha extraction gate.
- Older releases are **not** retroactively updated. v0.9.0a1 remains a published, immutable release; the extraction lands in v0.9.0a2's release artifacts.

### What the founder reviews at ADR-008 graduation

A graduation PR should include:
1. The five gate artifacts above
2. The ROADMAP.md supported-surface update
3. The CHANGELOG entry under `### Added` for the graduating release
4. The `experimental/<feature>/STATUS.md` flip from Experimental → Graduated with all five gate dates
5. The `concepts/features.md` row update
6. The `compatibility-matrix.yaml` update

CI rejects a graduation PR that's missing any of those artifacts (per ADR-013 deprecation-policy validator pattern + ADR-008 gate-tracking).

---

## How to follow along

- **Public engineering log:** Friday weekly post in `docs/blog/` (alpha-series onwards).
- **CHANGELOG.md** at repo root — Keep-a-Changelog format.
- **GitHub Project — "Stigmem GA Readiness Plan":** [Eidetic-Labs/projects/1](https://github.com/orgs/Eidetic-Labs/projects/1) (flips public at v0.9.0a1 retraction).
- **ADR index:** [`docs/adr/README.md`](docs/adr/README.md).
- **Compatibility matrix** (lands during the beta series): published at `docs.stigmem.dev/operate/compatibility`.
- **Model certification list** (lands during the beta series, per ADR-015): published at `docs.stigmem.dev/secure/model-certification`.

---

## Stability commitments by version line

Per [ADR-001](docs/adr/001-versioning.md) + [ADR-013](docs/adr/013-deprecation-policy.md):

- **Pre-1.0 (`v0.9.0aN`, `v0.9.0bN`, `v1.0.0rcN`):** No stability guarantee. Breaking changes in any release; pin to specific versions; auto-upgrade is not safe.
- **`v1.0.0` and `v1.x`:** Wire format and public Python API are stable. Removing a public API requires a deprecation in v1.x followed by removal no earlier than v2.0.0.
- **Deprecated features:** supported through the rest of the major version they were deprecated in.
- **Experimental features:** subject to breaking changes in any release without notice; their use behind feature flags is at-your-own-risk.

---

*Roadmap is a living document. Updates land alongside ADR amendments and version-line transitions. Contributions to roadmap shaping go through the ADR amendment process per [ADR-001](docs/adr/001-versioning.md) §Contributor approval rule.*
