# ADR-013: Deprecation policy

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** ADR-001 (versioning), ADR-005 (docs IA), ADR-008 (experimental gates), ADR-012 (version-aware feature exposure), ADR-014 (compatibility matrix); `stigmem/analyses/docs-structure-review-2026-05-06.md`

---

## Context

Stigmem has no documented deprecation policy. The retraction of v1.0 / v2.0 was effectively a deprecation event with no policy infrastructure behind it: features were announced as stable, then removed without a defined notice window, replacement path, or compatibility commitment.

Three things have to be true for federation infrastructure to attract serious operators:

1. **Predictable change.** Operators need to know how long they have to adapt to a deprecation before code stops working. "Soon" is not a deprecation policy.
2. **Replacement clarity.** Every deprecated surface must point at what replaces it. Deprecating without a replacement is just a removal with extra steps.
3. **Compatibility commitment.** A written commitment about what stigmem will not break, scaled to project resources.

Industry practice in the closest analogues:

- **Kubernetes** — explicit version-distance commitment: "stable APIs cannot be removed for at least 12 months or 3 releases, whichever is longer." Beta APIs deprecated for at least 9 months or 3 releases.
- **Python** — `Deprecated since version X.Y` annotation; removed typically two minor releases later (Python's deprecation cycle is well documented in PEPs).
- **Stripe** — long deprecation tails; old API versions supported indefinitely; warnings via response headers.
- **Node.js** — DEP-XXX deprecation codes, runtime warnings, end-of-life schedule per release line.
- **AWS SDKs** — deprecation announcement → minor-version deprecation → removal in next major; scheduled with explicit dates.

Stripe's "supported indefinitely" policy is unattainable for a small team; Node's DEP-XXX runtime warning system is overkill for v0.9.0-preview. Kubernetes' version-distance approach is the right scale: predictable, explicit, and decoupled from calendar dates.

## Decision

### The policy

A feature in stigmem follows this lifecycle:

```
stable → deprecated → removed
                        (no earlier than next major)
```

Specifically:

1. **Stability annotations are version-distance commitments.** A `stable` feature in v0.9.0-preview will not break in any patch or minor release within the 0.9.x line.
2. **Deprecation requires a major version of notice.** A feature deprecated in vX.Y is supported through all subsequent vX.* releases, and may be removed no earlier than vX+1.0 stable.
3. **Beta features carry a shorter commitment** — deprecated in vX.Y, removable in vX.Y+1. Beta features are not stable promises.
4. **Experimental features may be removed without notice in the next release.** That's the deal: experimental features ship behind flags so users can try them, but no compatibility commitment applies.

### Required artifacts at deprecation

When a feature is marked `stability: deprecated` in its frontmatter (per ADR-012), the same PR ships:

- Updated `<Stability level="deprecated" />` banner on the feature page with `removed_in:` and `replacement:` frontmatter values present.
- A migration-note section on the feature page describing how to move to the replacement.
- A CHANGELOG entry under `### Deprecated` for the release that introduces the deprecation.
- A row in the `Reference → Deprecated features` aggregate page (auto-generated from frontmatter where `stability == deprecated`).
- If the deprecation has wire-format implications, a documented `Stigmem-Version` upgrade path (per ADR-012).

The PR cannot land if any of these artifacts are missing. CI validator (extended from ADR-012's plugin) enforces.

### Compatibility commitment doc

A canonical `docs/docs/secure/compatibility-commitment.md` page states the commitment in plain language:

- **Stable features** in v1.0 will not have wire-format breaking changes through v1.x.
- **Deprecated features** are supported through the rest of the major version they were deprecated in, removed no earlier than the next major.
- **Beta features** are subject to breaking changes in the next minor release, with a CHANGELOG entry per change.
- **Experimental features** are subject to breaking changes in any release without notice; their use behind feature flags is at-your-own-risk.
- **Wire-format pinning** via the `Stigmem-Version` header (per ADR-012) is honored across at least one major version after a feature is deprecated.

The commitment doc is reviewed at every major release. Any tightening or loosening goes through an ADR amendment.

### Aggregate `Deprecated features` page

A page at `Reference → Deprecated features` (or `Build → Deprecated features` post-IA-restructure) is auto-generated from frontmatter and lists, per release:

- Feature name and link to its current page.
- `since` (when introduced).
- `deprecated_since` (when marked deprecated).
- `removed_in` (planned removal version).
- `replacement` (link to replacement, if any).
- Migration note summary.

The page is generated at build time by a Docusaurus plugin (extending the ADR-012 frontmatter validator); operators planning an upgrade have a single place to audit.

### Deprecation kinds

Three kinds, each with slightly different artifact requirements:

| Kind | Example | Required artifacts |
|---|---|---|
| **Wire-format deprecation** | A spec section is deprecated; old wire format still accepted but warned. | All standard artifacts + `Stigmem-Version` header behavior + spec amendment. |
| **API surface deprecation** | An SDK method is deprecated in favor of a new one. | All standard artifacts + SDK release note + runtime deprecation warning (where idiomatic for the language). |
| **Operational deprecation** | An env var, config key, or runbook is replaced. | All standard artifacts + startup log warning when the deprecated config is in use. |

For wire-format deprecations specifically, the server emits a `Stigmem-Deprecation: feature-name` response header on requests that exercise the deprecated surface. SDKs surface this as a logged warning.

## Alternatives considered

**1. Time-based deprecation (e.g., "deprecated features supported for 12 months").** Rejected. Couples to calendar; conflicts with the project-wide phase-gated convention; assumes a release cadence that the project hasn't committed to. Version-distance is the right unit.

**2. One-version-warning policy (deprecated in vX.Y, removed in vX.Y+1).** Rejected as too short. A one-minor-version window is not enough for serious adopters to plan migrations, especially given typical enterprise upgrade cycles.

**3. Indefinite support for deprecated features (Stripe-style).** Rejected. Indefinite support accumulates dead surface and complexity; a small team cannot sustain it. The Kubernetes-style commitment is the right balance: long enough to be useful, bounded enough to be sustainable.

**4. No formal policy; communicate deprecations in release notes only.** Rejected. The retraction is an existence proof that ad-hoc communication is insufficient. A written policy is part of credibility, not an extra.

**5. DEP-XXX-style numbered deprecations (Node.js).** Considered. Rejected for v0.9.0-preview as overkill — the surface is small enough that named deprecations are more readable than numbered codes. Reconsider if deprecations exceed ~20 active items.

## Consequences

### What gets easier

- **Operators can plan upgrades** with a clear contract about what will and won't break.
- **Contributors have a clear bar** for when to mark something deprecated and what to ship with it.
- **Trust signaling.** A written deprecation policy is what credible infrastructure projects have. Its absence was part of what made v1.0 / v2.0 retraction necessary.
- **Aggregate auditability.** The auto-generated deprecated-features page is one source of truth for upgrade-planning audits.

### What gets harder

- **One-major-version support tail.** Every deprecated feature must continue working through the rest of its major-version line. Code complexity accumulates; mitigation is the version-distance bound (vs. indefinite).
- **CI validator complexity.** Enforcing the artifact-set on every deprecation PR adds plugin logic to the docs CI. ~1 day to implement; small ongoing maintenance cost.
- **Compatibility-commitment doc as a contract.** Once written and accepted, the doc binds the project. Mitigation: ADR amendment process exists; the commitment can be tightened or loosened with explicit reasoning.

### New risks

- **R-DEP-1: deprecation backlog.** Features get marked deprecated but the team doesn't have capacity to actually remove them at vX+1. The deprecation queue grows. Mitigation: the deprecated-features page is a visible queue; phase-exit checklists at major releases include "deprecation queue review."
- **R-DEP-2: deprecation-without-replacement.** A feature is deprecated for legitimate reasons (security, design change) but no replacement exists yet. Mitigation: the policy requires `replacement:` to be set; if no replacement exists, the feature is `removed`, not `deprecated`, with a CHANGELOG entry under `### Removed`. Hard removal is honest about what happened; deprecation-without-replacement is theater.
- **R-DEP-3: third-party dependencies on experimental features.** Even though experimental features carry no compatibility commitment, third parties may build on them and complain when they break. Mitigation: feature-flag default-off behavior (per ADR-002 + ADR-011) means third parties opt in explicitly; experimental status is a banner the user has to dismiss to use; the policy is documented at multiple levels (frontmatter + commitment doc + CHANGELOG).

## Implementation plan

Lands in master-checklist §4.3a (PR 2.5 — Docs site restructure and reversion sweep) as the policy doc and CI infrastructure. Per-feature deprecation tracking begins immediately and applies to the retraction:

- Write `docs/docs/secure/compatibility-commitment.md` with the commitment text.
- Extend the ADR-012 frontmatter validator to require `removed_in:` and `replacement:` when `stability: deprecated`.
- Add the auto-generated `Deprecated features` page (Docusaurus plugin extending the ADR-012 index generator).
- Add `Stigmem-Deprecation` response-header support to the node (Phase B, slot near ADR-012's `Stigmem-Version` work).
- Document the policy in `CONTRIBUTING.md` so contributors know what artifacts a deprecation PR requires.
- Apply the policy retroactively to the retraction: every v1.0 / v2.0 feature that's not making it to v0.9.0-preview gets either a `removed` entry in CHANGELOG or a `deprecated` annotation if it's preserved in `experimental/` for future reintroduction.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*