# ADR-001: Versioning, phases, and stability commitments

**Status:** Accepted
**Amended by:** ADR-019 (2026-05-08) — pre-release version-string convention updated from `v0.9.0-preview` to PEP 440 / semver alpha-beta-rc; per-ecosystem spelling spelled out; surface inventory delegated to `release/version-surfaces.yaml`. ADR-001's body is preserved as the historical record of the original decision; readers should consult ADR-019 for the current convention.
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** `stigmem/plans/strengthening-plan.md`, `LIMITATIONS.md`, migration post

---

## Context

In the first week of public release, the project shipped under five different version states simultaneously:

| Source | Version |
|---|---|
| `README.md` | "v1.0 stable · Phase 7 (substrate)" |
| `pyproject.toml` | `1.0.0rc1` |
| `SECURITY.md` | "v1.0-rc" |
| `spec/security/threat-model.md` | "v1.1-draft" |
| Recent commits | "v2.0 migration guide and release notes" |

This inconsistency was the visible symptom of a deeper issue. The "v1.0" label was withdrawn because several controls our threat model identified as required for that release — mTLS, audit log, rate limits, key expiry, capability validation — were still in flight.

The follow-up review surfaced an even more fundamental problem: stigmem had never had a real release. The version labels v0.2 through v2.0 that appeared in `spec/`, `versioned_docs/`, and CHANGELOG entries described internal development checkpoints, not tagged releases anyone deployed in production. The project was carrying a multi-version history it hadn't earned. Naming those checkpoints as "previous releases" overstated project maturity in the same way the v1.0 announcement did. (Important distinction: the spec *content* under those labels is real product specification — it is reviewed and migrated forward into v0.9.0-preview, not deleted. Only the implied release chronology is being corrected.)

**v0.9.0-preview is therefore declared as the *first build* of stigmem.** The canonical version line begins here. Prior version *markers* (v0.2 through v2.0) labeled development checkpoints, not tagged releases — they are not part of the SemVer chronology. The spec *content* under those markers is real protocol specification; it is reviewed section by section against actual implementation and migrated forward into the v0.9.0-preview canonical spec (per master-checklist §4.3a). Earlier evolutionary spec files move to `spec/archive/evolution/` as reference material *after* their content has been reviewed and forward-migrated, with header pointers to the canonical equivalents. The spec is preserved and improved, not archived as history.

We also adopted internal "phase" markers (Phase 7, Phase 12) for sprint planning, and these appeared in externally-facing documents — README, threat model, SECURITY.md. Adopters do not know what "Phase 12" means, and the inconsistency made the project look like an internal initiative rather than a public release.

A federated agent-memory protocol earns trust over years, not weeks. We want version labels that mean what they say, enforceable in CI, with a clean separation between externally-facing version names and internally-facing sprint markers — and a clean starting point that doesn't carry imaginary release history.

## Decision

We adopt the following versioning scheme.

### Externally-facing version names — SemVer

We will use [Semantic Versioning 2.0.0](https://semver.org/) for all externally-facing version labels. The version sequence across the strengthening-plan phases is:

| Label | Meaning | Wire-format stability |
|---|---|---|
| `v0.9.0-preview` | Hardened-core development; not for adversarial deployment. Breaking changes during the window are expected and called out in the changelog. | Unstable |
| `v0.9.x` | Successive preview releases as Phase B work lands. | Unstable |
| `v1.0.0-rc.N` | Release candidates after Phase B is feature-complete. RC is announced with the start of the 30-day external operator soak. | Wire format frozen at `v1.0`; bug-fixes only |
| `v1.0.0` | General availability. Wire-format committed. Backwards compatibility guaranteed within the v1.x line. | Stable |
| `v1.x.x` | Patches and additive changes that preserve v1.0 wire format. | Stable |
| `v2.0.0-experimental.N` | Re-introduction of cut features, one at a time, behind feature flags. Defaults off. | Forward-compatible with v1.x |
| `v2.0.0` | Future major release. Wire-format breaking changes permitted; will not happen until at least three external operators are running v1.x in production. | Stable |

### Internally-facing sprint markers — phases

Phases (Phase 7, Phase 12, etc.) remain valid as internal sprint markers and may appear in commit messages, internal planning docs, and the strengthening plan. They **must not** appear in:

- README, LICENSE, LIMITATIONS.md, SECURITY.md, ROADMAP.md
- Released package metadata (`pyproject.toml`, `package.json`)
- The docs site (`docs.stigmem.dev`)
- Threat model, scenarios, or operator-facing security documents
- Release notes or changelog entries
- Any external-facing announcement, blog post, or social media

### Stability commitments per release

- **Pre-1.0 (`v0.9.x`, `v1.0.0-rc.N`):** No stability guarantee. Breaking changes are documented in the changelog under a `BREAKING` section. Operators pin to specific versions; auto-upgrade is not safe.
- **`v1.0.0` and `v1.x`:** Wire format and public Python API are stable. Removing a public API requires a deprecation in v1.x followed by removal in v2.0. New features are additive.
- **`v2.0.0-experimental.N`:** Each experimental feature has its own independent lifecycle. A feature may be promoted to v1.x as additive (no breaking change) or wait for v2.0.0 stable (breaking changes permitted).

### Version-consistency enforcement

A CI check (`scripts/check_version_consistency.py`) reads the canonical version from `pyproject.toml` and asserts that every other version string in the repository agrees:

- `README.md` (release banner, install instructions)
- `package.json`
- Docusaurus config (`docs/docusaurus.config.js`)
- All spec frontmatter
- `SECURITY.md` "Applies to" line
- Threat model "Applies to" line
- Scenarios "Applies to" line
- LIMITATIONS.md "Applies to" line

The check fails the PR on any disagreement.

### Contributor approval rule (project-wide)

The team is two contributors, including the founder. The approval rule for ADRs, ADR amendments, and PRs is:

> **Sign-off on any ADR (or amendment) and on any PR through Phase B requires *either* two contributors *or* the founder alone.**

Founder solo-approval exists because the project has a small team and one contributor's unavailability would otherwise stop work entirely. The founder takes responsibility for the validation discipline whenever they sign off alone — the guardrail that two-person review provides against AI-velocity-outrunning-validation (per the v1.0 retraction narrative) lives with the founder when they approve solo. This is a deliberate exchange: review surface is reduced to the founder's individual judgment in those cases; the founder owns the consequences.

This rule applies to:
- ADR acceptance (Proposed → Accepted).
- ADR amendments (any changes after acceptance, per each ADR's Amendment process).
- PR review through Phase B (the strengthening-plan period during which review discipline is most acute).
- Threat-model deltas (per ADR-008 Gate 1).
- Any other process step that this corpus describes as requiring "two contributors' sign-off."

Documents that reference "two contributors" sign-off should be read as "two contributors or the founder alone."

## Alternatives considered

**1. Keep the v1.0 / v2.0 dual-track and clarify with banners.** Rejected. The migration post commits to repositioning v1.0 publicly; continuing to advertise both labels would re-create the original confusion. The v0.9.0-preview reset is the cleanest correction.

**2. Use CalVer (`2026.05.0`) instead of SemVer.** Rejected. CalVer works for projects whose meaningful unit is "what shipped this month." Stigmem's meaningful unit is "what's the wire-format compatibility surface." SemVer maps to that question; CalVer doesn't.

**3. Skip the `-preview` suffix and version v0.9.0 directly.** Rejected. The suffix is deliberate signal: it tells package managers (PyPI, npm) to treat this as a pre-release that pinned upgrades won't auto-pick up. Bare `v0.9.0` would silently upgrade installs that haven't pinned.

**4. Drop phase markers entirely.** Rejected for internal use. Phases are useful sprint-tracking shorthand internally and there's no harm in them as long as they don't leak. The leakage is the problem, not the existence.

## Consequences

### What gets easier

- **Single source of truth.** Anyone reading the project knows exactly what `v0.9.0-preview` means, what it commits to, and what it doesn't.
- **External communication.** Adopters, operators, and contributors share a vocabulary. "When does mTLS-default ship?" has a single answer ("v0.9.x"); "when is wire format stable?" has a single answer ("v1.0.0").
- **CI enforcement.** Version drift becomes a hard error, not a culture norm. Future releases cannot accidentally re-create the five-version-state problem.
- **Roadmap clarity.** The public roadmap can use version labels that match what gets shipped.

### What gets harder

- **Discipline cost.** Every pull request now checks version-string consistency. Mechanical, but real.
- **No "we'll just call it v1.0 for the announcement and clean up later."** This ADR commits the project to version labels that match validation status.
- **Phase markers in internal docs require care.** Anyone writing a doc that *might* end up externally visible must check whether phase references are appropriate.

### New risks

- **R-DOC-1:** Version strings exist in places not enumerated above (e.g., embedded in code as Python module constants, in test fixtures). The CI check must be expanded as new locations are introduced. Mitigation: keep the check's grep patterns broad and run it on every PR.
- **R-DOC-2:** External documentation hosted off-repo (blog posts, slide decks, talks) can drift from the canonical version. Mitigation: announce the convention in the migration post; add a one-line "Versioning conventions" section to the docs front page that external authors can link to.

### Migration

This ADR is effective immediately. Phase A of the strengthening plan includes the version-sweep PR that brings every file into alignment with the canonical version (`0.9.0`). The CI check ships in the same PR.

## Open questions

- **Should `-preview` releases be installable via `pip install stigmem` (default channel) or require `pip install --pre stigmem`?** Recommended: `--pre` only, so default installs of stigmem on a system where someone hasn't read the docs go to whatever the latest stable is (currently nothing — they will see "no matching distribution found" until v1.0.0 ships, which is correct behavior).

- **What does an experimental feature's version look like when it's promoted from `v2.0.0-experimental.N` into `v1.x`?** Recommended: it joins the v1.x line with a feature flag default-off, and the experimental release is marked superseded. ADR-008 governs the promotion gates.

These are deferred to follow-up ADRs as the questions become live.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*