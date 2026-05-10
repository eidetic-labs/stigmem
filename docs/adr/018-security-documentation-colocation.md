# ADR-018: Per-feature security documentation colocation

**Status:** Accepted
**Date:** 2026-05-07
**Authors:** Eidetic Labs
**Related:** ADR-008 (experimental gates), ADR-009 (repo structure), ADR-010 (modular specs), ADR-011 (C1 plugin architecture), ADR-015 (adversarial conformance and model certification), ADR-016 (storage immutability), ADR-017 (CIDs as core); threat model

---

## Context

ADR-010 commits the project to modular per-topic specs that **colocate with features**: experimental specs live at `experimental/<feature>/spec.md`, alongside the feature's code, tests, migrations, integration docs, and conformance vectors (per ADR-009 § 2(a) plugin package layout). The pattern produces clear ownership: a feature's spec travels with the feature; reintroduction (per ADR-008 gates) brings them back together.

Security documentation does not follow that pattern. The current state:

- **Protocol-level security artifacts** live at `spec/security/threat-model.md` (unified risk register) and in `docs/Secure/` once the ADR-005 IA migration lands (overview, scenarios, hardening guide, advisories, disclosure policy).
- **Per-feature security analysis is scattered.** R-15 (instruction-scope injection) is about §21 lazy instruction discovery, but R-15's content lives in the protocol-level threat model, not alongside §21. R-16 and R-17 are about §23 RTBF tombstones; same pattern. R-21 (worm vector) is cross-cutting and touches multiple features. R-23 (admin storage tampering, per ADR-016) is cross-cutting at the protocol level.

When a feature lives at `experimental/<feature>/`, its security analysis does not. Two consequences:

1. **Asymmetry with ADR-010.** A spec migrates with the feature it specifies; the security analysis for that same feature does not. This breaks the "feature self-contained at `experimental/<feature>/`" principle.
2. **Discoverability.** Reading the lazy-instruction-discovery directory tells you what the feature does and how it's tested but not what its risks are. The risks are in a different file in a different directory.
3. **Reintroduction friction.** When a feature graduates per ADR-008's gates, its security analysis must be located, evaluated, and updated. Locating is harder than it should be when the analysis is in a separate document.
4. **Threat-model bloat.** As experimental features accumulate, their entries in the protocol-level threat model accumulate too. The threat model becomes unreadable to operators looking for cross-cutting risks (HLC, supply chain, storage tampering) buried among per-feature deferred-feature risks.

This ADR establishes the same colocation pattern ADR-010 uses for specs, applied to security artifacts. Per-feature security analysis lives with the feature; the protocol-level threat model becomes a hub document that focuses on cross-cutting risks and references per-feature analysis.

## Decision

We restructure security documentation into two tiers, mirroring the ADR-010 spec model:

### Tier 1: Protocol-level security artifacts (the hub)

These live at `spec/security/` (canonical source) and render in `docs/Secure/` per ADR-005 IA:

- **`spec/security/threat-model.md`** — the unified risk register. Lists all R-XX entries with status (Mitigated / Residual / Open / Accepted). Cross-cutting risks (R-19 HLC, R-20 embedding poisoning, R-22 supply chain, R-23 admin storage tampering) include their full analysis here. Per-feature risks include a brief summary and link to `experimental/<feature>/security.md` for full analysis.
- **`spec/security/architecture.md`** — protocol-level security architecture: capability tokens, audit log, federation trust, mTLS, key rotation. Cross-cutting; not feature-specific.
- **`spec/security/disclosure.md`** — security disclosure policy and procedures.
- **`spec/security/advisories/`** — per-disclosure advisory artifacts.
- **`spec/security/scenarios.md`** — operator-facing narratives. May reference per-feature scenarios; does not duplicate them.

### Tier 2: Per-feature security artifacts (colocated)

Each `experimental/<feature>/` directory gains a `security.md` file with the following structure:

```yaml
---
feature: <feature-name>
spec_id: Spec-X<N>-<Topic>
status: Experimental | Stable | Deprecated
applies_to: stigmem v0.9.0-preview
last_updated: YYYY-MM-DD
---
```

Followed by sections:

```markdown
## Owned risks

Risks for which this feature is the primary subject. Each entry mirrors the protocol-level threat-model format (Risk ID, STRIDE category, description, likelihood, impact, severity, control, status, mitigation).

## Contributed risks

Risks for which this feature is a contributor but not the primary subject. Cross-link to the canonical entry.

## Threat model delta (for ADR-008 Gate 1)

If this feature graduates back to core, what changes about the protocol's threat surface? Listed as additions to the protocol-level threat model.

## Operator scenarios

Plain-English narratives where this feature creates risk for operators. May be cross-referenced from `spec/security/scenarios.md`.

## Conformance pointers

Which categories of the adversarial conformance corpus (per ADR-015) exercise this feature's security properties. Cross-link to corpus pattern files.

## Reintroduction gates (per ADR-008)

Specific evidence required for this feature's security work to pass each ADR-008 gate. Owners check these off as gates are met.

## Cross-references

- Spec: `experimental/<feature>/spec.md` (Spec-X<N>)
- ADRs: any ADR that bears on this feature's security
- Master-checklist sections
```

### Owned vs contributed risks

A risk has exactly one **owning feature** and zero or more **contributing features**. The owning feature's `security.md` carries the canonical analysis; contributors carry brief cross-listings that link to the canonical entry. This avoids duplication while making the cross-feature connections explicit.

Cross-cutting risks (those with no single owning feature) live exclusively at protocol level: R-01 through R-04, R-09, R-10–R-14, R-19, R-20, R-22, R-23. These are not duplicated in any per-feature `security.md`.

Per-feature owned risks (initial mapping based on existing R-XX entries):

| Risk | Owning feature | Per-feature `security.md` location |
|---|---|---|
| R-15 (instruction-scope injection) | lazy-instruction-discovery | `experimental/lazy-instruction-discovery/security.md` |
| R-16 (RTBF compliance gap) | tombstones | `experimental/tombstones/security.md` |
| R-17 (RTBF propagation drift) | tombstones | `experimental/tombstones/security.md` |
| R-18 (CID integrity) | (none — CID is core per ADR-017) | `spec/security/threat-model.md` (cross-cutting) |
| R-21 (agent feedback-loop worm) | (cross-cutting; touches lazy-instruction-discovery + memory-garden-acl) | `spec/security/threat-model.md` (cross-cutting) |

R-18 and R-21 are explicitly noted because they could plausibly be feature-owned but aren't: R-18 belongs to core (CIDs are core per ADR-017); R-21 is structurally cross-cutting (the worm vector spans multiple features by design).

### Status track for risks

Risks track status independently per the existing threat-model format: **Mitigated / Residual / Open / Accepted**. The status applies to the risk in the context of the current protocol release composition. A risk owned by an experimental feature can be `Open` in the protocol composition without affecting other features' status.

### Cross-reference conventions

Mirroring ADR-010's spec cross-references:

**From `spec/security/threat-model.md` to a per-feature `security.md`:**

> R-15 — see `experimental/lazy-instruction-discovery/security.md` for canonical analysis. **Status:** Open in v0.9.0-preview.

**From `experimental/<feature>/security.md` to the protocol-level threat model:**

> This risk is registered as R-15 in `spec/security/threat-model.md`. The canonical risk-register entry is here.

**Cross-feature contribution:**

> This feature contributes to R-21 (worm vector); the canonical analysis is in `spec/security/threat-model.md`. This feature's contribution: the lazy-instruction-discovery code path is one of the writer-key escalation paths the worm vector exploits.

### CI validation

A `scripts/check_security_documentation.py` validator runs in CI:

- Every R-XX entry in `spec/security/threat-model.md` either has full analysis at the protocol level OR points at an existing `experimental/<feature>/security.md`.
- Every `experimental/<feature>/security.md` exists for a feature that exists in `experimental/`.
- Every "owned risk" in a per-feature security doc has a corresponding entry in the protocol-level threat model.
- Cross-references resolve (no broken file paths or risk IDs).
- Frontmatter validates against the schema.

### What this ADR does NOT change

- The unified risk register format (per-risk status, STRIDE category, etc.) is unchanged. This ADR moves *where* risk analyses live, not how they're structured.
- ADRs are not relocated. ADR-003, ADR-016, etc., stay in the ADR sequence; they reference per-feature security docs as needed.
- The audit log, capability model, and other protocol-level security primitives stay protocol-level.
- The disclosure policy and advisory templates stay protocol-level.

## Alternatives considered

**1. Keep all security analysis at protocol level (status quo).** Rejected. Asymmetric with ADR-010; per-feature analysis becomes harder to find as features accumulate. The threat model bloats with per-feature noise that obscures cross-cutting risks.

**2. Keep all security analysis at protocol level but improve the threat model's organization (e.g., per-feature subsections).** Rejected. Improves discoverability but doesn't solve the colocation problem: when a feature is in `experimental/`, its security analysis still doesn't travel with it. Reintroduction per ADR-008 still requires fishing security context out of a separate document.

**3. Split security entirely per-feature (no protocol-level threat model).** Rejected. Cross-cutting risks (R-19 HLC, R-22 supply chain, R-23 admin tampering) don't decompose to a single feature. Protocol-level analysis is the right home for them. Operators and security auditors need a single document that names all the risks; a forest of per-feature docs without a hub is unreadable.

**4. Auto-generate the protocol-level threat model from per-feature `security.md` docs.** Considered. Mirrors ADR-010's `PROTOCOL.md` generation. Rejected for v1.0 because cross-cutting risks need authored prose that doesn't decompose; a partial auto-generation pattern (per-feature sections auto-generated, cross-cutting sections hand-authored) is more complex than it's worth. Reconsider if the threat model becomes large enough to justify the tooling.

**5. Use ADRs themselves as the per-feature security documents.** Rejected. ADRs document architectural decisions; security documents are living analysis that evolves with the feature's risk landscape. ADRs are immutable once accepted; security documents must be updatable as new analysis lands. They serve different purposes; conflating them breaks both.

## Consequences

### What gets easier

- **Per-feature self-containment.** A reader of `experimental/lazy-instruction-discovery/` sees the spec, the code, the tests, *and* the security analysis. No fishing in separate documents.
- **Reintroduction discipline.** ADR-008's gate process (threat-model delta required at Gate 1) has a natural home for the delta — it's drafted in the per-feature `security.md` and merged into the protocol-level threat model when the feature graduates.
- **Threat model stays focused.** The protocol-level threat model concentrates on cross-cutting risks and architecture. Per-feature noise lives with the feature.
- **Cross-references are first-class.** CI validates that risk IDs and file paths resolve; tooling can build a dependency graph between cross-feature contributions.
- **Symmetric with ADR-010 specs.** "Open the feature directory; everything is there" applies to spec and security alike. Consistent mental model for contributors.

### What gets harder

- **Migration cost.** Existing per-feature R-XX entries in the threat model need to be relocated to per-feature security.md files. ~1-2 days of mechanical work.
- **Cross-cutting analysis discipline.** Authors must decide whether a new risk is feature-owned or cross-cutting. Mistakes are easy ("this risk feels like it's about feature X, but actually it's cross-cutting"). Mitigation: protocol-level threat model is the default home for ambiguous cases; reclassification is fine.
- **Two-place updates for contributed risks.** A risk contributed-to by multiple features requires updates in the canonical location plus brief notes in each contributor's `security.md`. Mitigation: contribution notes are short by convention; CI catches broken cross-refs.
- **Tooling overhead.** The CI validator needs to be written. ~3-5 days. Same approach as ADR-010's spec generator.

### New risks

- **R-SEC-DOC-1: per-feature security drifts from protocol-level threat model.** A per-feature `security.md` could record an R-XX entry as Mitigated while the protocol-level threat model still says Open. Mitigation: CI validator checks that risk status is consistent across the canonical entry and any cross-listings.
- **R-SEC-DOC-2: cross-cutting risk gets misclassified as feature-owned.** A risk that should be at protocol level lands in a per-feature security.md; cross-cutting analysis is lost. Mitigation: ADR-008 gate review checks for this; security maintainer (founder by default) catches misclassifications during quarterly threat-model review.
- **R-SEC-DOC-3: feature deprecation orphans security analysis.** A feature deprecated per ADR-013 may have unresolved risks; if the per-feature `security.md` is removed, the analysis is lost. Mitigation: deprecated features' `security.md` remains in `experimental/<feature>/` with a Deprecated banner; risks are reviewed for migration to protocol level if still relevant.
- **R-SEC-DOC-4: empty or stale per-feature security.md files.** A new feature might land with `security.md` that's just frontmatter and no analysis. Mitigation: ADR-008 gate 1 (threat-model delta) requires a populated security.md before reintroduction; new experimental features must ship with at least an "Owned risks: none identified" + "Open questions" section.

## Implementation plan

This ADR's implementation is a Phase B deliverable, sequenced after ADR-010's spec migration completes (so the layout is stable) and after ADR-016's threat additions land (so R-23 and related are in place).

**Step 1 — Author per-feature `security.md` files (~1-2 days).**

For each `experimental/<feature>/`:
- Identify owned risks from the protocol-level threat model.
- Extract owned-risk entries into `experimental/<feature>/security.md` with frontmatter.
- Replace the protocol-level entry with a brief summary + cross-link.
- Add Threat-model-delta, Conformance pointers, Reintroduction gates sections (initially populated from ADR-008 gate-1 work).

**Step 2 — Refactor protocol-level threat model (~3-5 days).**

- Update `spec/security/threat-model.md` to reflect the new structure: full content for cross-cutting risks; brief summaries for feature-owned risks with cross-links.
- Update `docs/Secure/Threat-model/` Docusaurus pages to render the same structure (per ADR-005 IA).

**Step 3 — CI validator (~3-5 days).**

- Write `scripts/check_security_documentation.py`.
- Validate frontmatter, cross-references, status consistency.
- Add CI step that runs the validator on every PR.

**Step 4 — Documentation (~1-2 days).**

- Update `CONTRIBUTING.md`: where security analysis goes for new features.
- Update ADR-008 (or note in the gate-1 process) that gate-1 deliverable lands in per-feature `security.md`.
- Update master-checklist §3 (artifact mapping) to reflect the new locations.
- Operator-facing doc at `docs/Secure/where-security-analysis-lives.md` so adopters can navigate the structure.

**Total:** ~1-2 weeks across Phase B, parallel with other security work.

## Open questions

- **Should `security.md` be required or optional for new experimental features?** Recommend: required. ADR-008 gate 1 (threat-model delta) is required for graduation; the natural place for that delta is `security.md`. Empty/stub `security.md` is acceptable at experimental status; populated `security.md` is required for graduation.
- **Should per-feature `security.md` use the same YAML frontmatter as `spec.md` (per ADR-010)?** Recommend: similar shape, different fields. Both carry `feature`, `status`, `applies_to`, `last_updated`. The spec frontmatter has `spec_id`, `version`, `depends_on`. The security frontmatter has different concerns (`reviewed_by`, `risk_count`, etc.). Document both schemas; share what's shareable.
- **Does this pattern extend to operator runbooks, performance benchmarks, compliance evidence?** Probably yes; out of scope for this ADR. ADR-018 establishes the precedent; future ADRs can apply the same pattern to other artifact classes if the symmetry helps.

## Amendment process

Changes to this ADR require sign-off per ADR-001 §Contributor approval rule (two contributors or the founder alone). Common amendment cases:

- Changing the per-feature schema (e.g., adding new sections).
- Adding new artifact classes that follow the colocation pattern.
- Changing what's classified as cross-cutting vs feature-owned.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*