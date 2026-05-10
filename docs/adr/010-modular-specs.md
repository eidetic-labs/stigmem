# ADR-010: Modular per-topic specs with independent versioning

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Supersedes:** Implicit monolithic spec model (`spec/stigmem-spec-vN.md`)
**Related:** ADR-001 (versioning), ADR-002 (v1 scope), ADR-008 (experimental gates), ADR-009 (repo structure)

---

## Context

The stigmem specification is currently maintained as a monolithic document — `spec/stigmem-spec-v1.0.md`, `spec/stigmem-spec-v2.0.md`, and so on — each version a single file containing all sections (§1 through §25). When the protocol moves forward, the entire document gets a new version number, regardless of whether the change touched §3 (core fact model) or §23 (RTBF tombstones).

This monolithic model has a structural property that the v1.0 release made visible: a single version number cannot represent content with different maturity levels. The v2.0 spec marked §21 lazy instruction discovery, §23 tombstones, §24 time-travel, and §25 CIDs as Normative because that's what shipping a single-version spec required. In reality:

- §1–§20 were genuinely solid (the federation primitives, capability tokens, manifests, audit log).
- §21–§25 were experimental: §21 had a Critical/High security risk (R-15) with no structural mitigation; §23–§25 had operational gaps that hadn't been operator-validated.

Because the monolithic version label can't selectively scope the maturity claim, repositioning the spec required reverting the whole document. Modular specs let each section's status track independently.

The same pattern affects every draft: the entire spec churns when one section changes, cross-references shift, and reviewers must distinguish substantive protocol changes from incidental rewrites of unrelated sections. The spec's version number is meaningful at the document level but not at the granularity of individual features.

The IETF, W3C, and MCP all solved this problem the same way: **modular specs, each independently versioned, composed via a meta-document that names which combination of specs constitutes a release.**

This ADR adopts that model.

## Decision

We restructure the spec from a single monolithic versioned document into a set of modular specs, each covering a single topic, each independently versioned, each with its own status track.

### Naming convention

Specs use the format `Spec-NN-Topic-Name` where `NN` is a stable two-digit identifier and `Topic-Name` is descriptive:

- `Spec-01-Core`
- `Spec-05-Federation-Trust`
- `Spec-09-Audit-Log`
- `Spec-X1-Lazy-Instruction-Discovery` (X-prefix for experimental specs)

The number is **stable across renames**. If a spec's topic name changes, the number stays. New specs get the next available number; numbers are never reused.

### Per-spec metadata

Every spec carries a YAML frontmatter block:

```yaml
---
spec_id: Spec-05-Federation-Trust
version: 1.0.0
status: Stable | Draft | Experimental | Superseded | Deprecated
applies_to: stigmem v0.9.0-preview
last_updated: 2026-05-06
supersedes: (if applicable) Spec-05-Federation-Trust v0.9.0
deprecated_by: (if applicable) Spec-NN-Replacement v1.0.0
depends_on:
 - Spec-01-Core >= 1.0.0
 - Spec-04-Manifests >= 1.0.0
---
```

This metadata is parseable; the meta-document (`spec/PROTOCOL.md`) is generated from it.

### Status track per spec

Independent of any other spec's status. A spec progresses through:

- **Draft** — under active development; contents may change incompatibly.
- **Experimental** — implementation exists but has not passed ADR-008 gates; not for production federation.
- **Stable** — committed contract; backwards compatibility guaranteed within the spec's major version.
- **Superseded** — replaced by a newer version of the same spec; old version preserved for reference.
- **Deprecated** — slated for removal; an end-of-life date is published.

A given spec can be Stable while a sibling spec is Experimental. The protocol release is the union of specs at their current versions.

### Independent semantic versioning per spec

Each spec follows SemVer 2.0.0 *for itself*. Spec-01-Core might be at v1.2.0 while Spec-13-Capability-Instructions is at v0.4.0-draft. Breaking changes within a spec require a major-version bump on that spec only. The protocol release version (per ADR-001) is a separate, higher-level commitment that names a specific combination of spec versions.

### The meta-document

`spec/PROTOCOL.md` is the index and release-composition document:

```markdown
# Stigmem Protocol — v0.9.0-preview

## Core specs (v1.0 candidates)

| Spec | Version | Status | Applies to |
|---|---|---|---|
| [Spec-01-Core](specs/01-core.md) | 1.0.0-rc.0 | Stable candidate | v0.9.0-preview |
| [Spec-04-Manifests](specs/04-manifests.md) | 1.0.0-rc.0 | Stable candidate | v0.9.0-preview |
| [Spec-05-Federation-Trust](specs/05-federation-trust.md) | 1.0.0-rc.0 | Stable candidate | v0.9.0-preview |
| ... | ... | ... | ... |

## Experimental specs (per ADR-008)

| Spec | Version | Status | Located at |
|---|---|---|---|
| Spec-X1-Lazy-Instruction-Discovery | 0.4.0-draft | Experimental | `experimental/21-lazy-instruction-discovery/spec.md` |
| Spec-X2-RTBF-Tombstones | 0.6.0-draft | Experimental | `experimental/23-rtbf-tombstones/spec.md` |
| ... | ... | ... | ... |

## Protocol release composition

A stigmem protocol release is the named combination of specs at specific versions.

| Protocol release | Composition |
|---|---|
| v0.9.0-preview | Spec-01@1.0.0-rc.0, Spec-04@1.0.0-rc.0, Spec-05@1.0.0-rc.0, ... (no experimental specs) |
| v1.0.0 (target) | Same as above with all -rc suffixes removed; each spec at its first stable version |
```

This document is auto-generated from spec frontmatter on every commit.

### Initial decomposition

The current monolithic v1.0 spec decomposes into approximately 14 core specs:

| Number | Topic | Maps from |
|---|---|---|
| Spec-01 | Core data model | §1–§5 |
| Spec-02 | Scopes and ACL | §3.5, §17 (core ACL only; advanced features in Spec-X5) |
| Spec-03 | HTTP API contract | API surface across §§ |
| Spec-04 | Manifests and Rekor | §19.1–§19.2 |
| Spec-05 | Federation trust | §19 (peer auth, replication) |
| Spec-06 | Capability tokens | §19.3 |
| Spec-07 | Recall pipeline | §6, §20 |
| Spec-08 | Quarantine garden | quarantine semantics |
| Spec-09 | Audit log | §22.3 |
| Spec-10 | Hardening | §22.1, §22.2, §22.4, §22.6 |
| Spec-11 | Replay protection | §22.5 |
| Spec-12 | HLC bounded skew | (new; per R-19) |
| Spec-13 | Capability-based instructions | (new; per ADR-003) |
| Spec-14 | Batch assert | (new; per ADR-006) |

Experimental specs map directly to the deferred features in `experimental/`:

| Number | Topic | Located at |
|---|---|---|
| Spec-X1 | Lazy instruction discovery | `experimental/21-lazy-instruction-discovery/spec.md` |
| Spec-X2 | RTBF tombstones | `experimental/23-rtbf-tombstones/spec.md` |
| Spec-X3 | Time-travel queries | `experimental/24-time-travel/spec.md` |
| Spec-X4 | Content-addressed IDs | `experimental/25-cids/spec.md` |
| Spec-X5 | Memory garden (advanced ACL) | `experimental/17-memory-garden/spec.md` |
| Spec-X6 | Source attestation | `experimental/18-source-attestation/spec.md` |
| Spec-X7 | Subscriptions | `experimental/subscriptions/spec.md` |

The `Spec-X*` prefix marks experimental specs; they live alongside the experimental code, not under `spec/specs/`.

### Cross-references

Specs reference each other by ID and version range:

> *This recall response format depends on `interpret_as` from Spec-13 ≥ 1.0.0.*

Cross-references that span the core/experimental boundary are tracked: a core spec MUST NOT have a hard dependency on an experimental spec. (Experimental specs may depend on core specs.)

### Layout on disk

```
spec/
├── README.md (overview; points at PROTOCOL.md)
├── PROTOCOL.md (auto-generated index of specs and release composition)
├── CHANGELOG.md (changelog at the protocol-release level)
├── specs/
│ ├── 01-core.md
│ ├── 02-scopes-and-acl.md
│ ├── 03-api.md
│ ├── 04-manifests.md
│ ├── 05-federation-trust.md
│ ├── ... (through Spec-14)
│ └── archive/ (superseded versions of individual specs)
│ └── 05-federation-trust-v0.9.md
├── design/ (existing — design docs and rationale)
├── security/ (existing — threat model, scenarios)
└── archive/
 ├── stigmem-spec-v0.2.md (the historical monolithic specs)
 ├── stigmem-spec-v1.0.md (superseded; preserved)
 └── stigmem-spec-v2.0.md (superseded; preserved)

experimental/
├── 21-lazy-instruction-discovery/
│ ├── STATUS.md
│ ├── spec.md (Spec-X1 lives here, alongside the feature)
│ └── ...
├── 23-rtbf-tombstones/
│ ├── STATUS.md
│ ├── spec.md (Spec-X2)
│ └── ...
└── ...
```

## Alternatives considered

**1. Keep the monolithic versioned spec; just be more careful about what we mark Normative.** Rejected. The v1.0 experience showed that careful-marking-within-a-monolith is not a stable discipline. Modular specs make the discipline structural rather than cultural.

**2. Numbered specs only (Spec-001, Spec-002), no descriptive names.** Rejected. RFC-style opaque numbers are stable but require an index for orientation. The hybrid `Spec-NN-Topic-Name` format gets the stability benefit and the readability benefit.

**3. Named specs only (Spec-Federation, Spec-Recall), no numbers.** Rejected. Renames become painful; cross-references break. The number is the stable identifier.

**4. One spec per spec section (one for §3.5, one for §3.6, etc.).** Rejected. Too granular. Specs should correspond to coherent topics that evolve together; section numbers within the current monolith are mostly artifacts of monolith-author convenience, not semantic boundaries.

**5. Defer the spec restructure until v1.0.0 GA.** Rejected. The v0.9.0-preview reset is the natural inflection point. Doing it later means the monolithic v0.9.0-preview spec exists as an interim artifact that has to be migrated separately.

**6. Adopt an existing spec-management framework (RFC tooling, W3C tooling).** Rejected for v1.0. Each of those frameworks adds significant tooling overhead. The hand-rolled approach in this ADR — markdown files with YAML frontmatter, a generated meta-document — is the lowest-overhead path that gets the structural benefit. Revisit at v1.x if the volume of specs justifies it.

## Consequences

### What gets easier

- **Selective experimental marking.** A new feature ships its own spec at status Experimental without affecting any other spec's status. No need to re-version the whole protocol.
- **Selective rollback.** If an experimental spec turns out to be flawed, only that spec rolls back. Repositioning a single spec is dramatically smaller in scope than repositioning a whole monolith.
- **Reviewable diffs.** Changes to Spec-22-Hardening don't churn the same file as unrelated Spec-17-Memory-Garden work. PR review focuses on actual semantic change.
- **Spec colocates with feature.** Experimental specs live in `experimental/<feature>/spec.md` alongside the code that implements them. Reintroduction (per ADR-008) brings spec and code back together.
- **Independent versioning communicates real maturity.** Adopters can see at a glance: "core specs are at v1.x; instruction discovery is at v0.4-draft." That's information the monolithic version label couldn't carry.
- **Cross-references become first-class.** Tooling can verify that `Spec-13 depends_on Spec-01 >= 1.0.0` is satisfied; the meta-document fails generation if a dependency isn't met.
- **Future experiments don't need to re-version the protocol.** Adding Spec-X8 doesn't require a v2.0 announcement; it just appears in the meta-document at its own version.

### What gets harder

- **Migration effort.** Decomposing the current monolithic spec into ~14 core specs plus ~7 experimental specs is real work. Estimate: 1 week of focused effort by one contributor.
- **Cross-reference discipline.** Internal references like "see §22.4" become "see Spec-10-Hardening section 4." Mechanical but ubiquitous; needs a sweep.
- **Tooling overhead.** The auto-generated PROTOCOL.md needs a generator script; YAML frontmatter validation needs a CI check.
- **External link rot.** Anyone who has linked to `spec/stigmem-spec-v1.0.md#section-22` has to update. Mitigation: redirects in the docs site; the v1 spec stays in `archive/` so old absolute links continue to work for read-only reference.
- **Cognitive shift for contributors.** "Open the spec and grep for the right section" becomes "find the right spec, then read it." Slightly slower for casual lookup; meaningfully faster for any focused work.

### New risks

- **R-SPEC-1: spec sprawl.** Once it's easy to add a new spec, the project might end up with 30 specs covering tiny topics. Mitigation: each spec needs a clear thematic boundary; the PR template asks "is this a new spec or an addition to an existing one?" New specs require ADR justification if their scope is narrow.
- **R-SPEC-2: dependency tangles.** Specs developing circular or deep dependencies become hard to evolve. Mitigation: dependency graph is auto-generated and reviewed periodically; circular dependencies are CI-blocked.
- **R-SPEC-3: PROTOCOL.md drift.** If the auto-generation breaks or stops running, the meta-document gets stale. Mitigation: PROTOCOL.md is generated as a CI step; non-trivially modified PROTOCOL.md fails CI (only the generator can write it).
- **R-SPEC-4: status-track inflation.** Operators and auditors might find five status levels (Draft / Experimental / Stable / Superseded / Deprecated) confusing. Mitigation: keep semantics tight; document each status explicitly with examples.

## Implementation plan

This ADR's implementation is a early Phase B deliverable in the strengthening plan, sequenced after the repo-structure cuts (ADR-009) land. Reasoning: ADR-009 creates `experimental/` and moves features there; the spec restructure populates each `experimental/<feature>/` with its `spec.md` and decomposes the core monolith.

**Step 1 — Decompose (Day 1–2):**
- Create `spec/specs/` directory.
- For each of the 14 core specs, extract the relevant content from `stigmem-spec-v1.0.md` into `spec/specs/NN-topic-name.md` with frontmatter.
- For each experimental feature, place its spec at `experimental/<feature>/spec.md` with frontmatter.

**Step 2 — Cross-reference sweep (Day 3):**
- Replace all internal `§N.M` references with `Spec-NN-Topic-Name section M.N` references.
- Update threat model, scenarios.md, ADRs, and code docstrings.

**Step 3 — Tooling (Day 4):**
- Write `scripts/generate_protocol_md.py` that reads spec frontmatter and produces `spec/PROTOCOL.md`.
- Add a CI step that runs the generator and fails if the result differs from the committed `PROTOCOL.md`.
- Add YAML frontmatter validation to CI.

**Step 4 — Archive (Day 5):**
- Move `stigmem-spec-v0.2.md` through `stigmem-spec-v2.0.md` to `spec/archive/`.
- Banner the archived v1.0 and v2.0 monolithic specs with pointers to the new modular structure.

**Step 5 — Documentation (Day 5):**
- Update `spec/README.md` to introduce the modular model and point at PROTOCOL.md.
- Update `docs/learn/` (per ADR-005) to reflect the new spec navigation.

## Open questions

- **Should patch-level versioning (e.g., Spec-01@1.0.1) be permitted, or only major.minor?** Recommend: full SemVer per spec. Patch versions cover editorial fixes and clarifications; minor versions cover additions; major versions cover breaking changes.

- **What's the right granularity for "compatible spec versions" in the meta-document?** The protocol release names exact spec versions today (`Spec-01@1.0.0`); should it instead name compatibility ranges (`Spec-01 >= 1.0.0, < 2.0.0`)? Recommend: exact versions for releases; ranges for development branches.

- **Should each spec carry its own changelog, or do all changes flow into the protocol-level CHANGELOG?** Recommend: per-spec changelog inside each spec file (a `## Changelog` section at the bottom); protocol-level CHANGELOG records release-composition events (e.g., "v0.9.0-preview: bumped Spec-13 from v0.4 to v0.5").

- **Does this decision affect how the spec is published to docs.stigmem.dev?** Slightly — each spec gets its own docs page (under the Build tab per ADR-005). The auto-generated PROTOCOL.md is the spec section's index page. Mostly mechanical Docusaurus configuration.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*