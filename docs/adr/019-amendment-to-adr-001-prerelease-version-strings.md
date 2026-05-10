# ADR-019: Amendment to ADR-001 — adopt PEP 440 / semver alpha-beta-rc convention for pre-release version strings

**Status:** Accepted (@offbyonce, 2026-05-08)
**Date:** 2026-05-08
**Authors:** Eidetic Labs
**Amends:** ADR-001 (Versioning, phases, stability commitments)
**Related:** ADR-012 (version-aware feature exposure), ADR-013 (deprecation policy), ADR-014 (compatibility matrix)

---

## Context

ADR-001 (Accepted 2026-05-06) declared the literal string **"v0.9.0-preview"** as the first build of stigmem and established the phase-to-version mapping for Phase A (reset), Phase B (hardened core), Phase C (v1.0 GA), and Phase D (post-1.0 expansion). The label "preview" was chosen as a descriptive marker meaning "pre-stable, first build."

Subsequent operational work (Phase A PR 0 execution, 2026-05-08) surfaced two problems with that literal string as the version emitted by `pyproject.toml`, `package.json`, and downstream artifacts:

1. **PEP 440 normalization.** The string "0.9.0-preview" is a *valid* PEP 440 version but normalizes to **"0.9.0rc0"**. Any wheel built from `version = "0.9.0-preview"` lands on PyPI as `stigmem 0.9.0rc0`. `pip show stigmem` returns `Version: 0.9.0rc0`. The user-facing label disappears at the Python packaging boundary and is replaced with a string ("rc0") that carries different connotations than "preview" — and worse, `rc` (release candidate) implies imminent stability, which is the opposite of what the retraction post communicates.

2. **No iteration convention.** A "preview" label has no built-in successor pattern. The phase plan anticipates multiple Phase A publishes (each PR that lands code wants a version). What follows "v0.9.0-preview" — "v0.9.0-preview-2"? "v0.9.1-preview"? Both PEP 440 and semver natively support iteration via `a1`, `a2`, `a3`, `b1`, `b2`, `rc1`, `rc2`. The convention is ecosystem-standard; "preview" is not.

A third consideration: ADR-014 (compatibility matrix) and ADR-013 (deprecation policy) both reference version strings as ordered identifiers for compatibility windows. PEP 440 / semver provide a strict-monotonic ordering. A "preview" label provides none.

This amendment replaces the literal "preview" version string with the alpha/beta/rc convention across all of stigmem's emitted version surfaces, while preserving "preview" and "experimental" as descriptive category language where useful.

## Decision

**Adopt PEP 440 / semver alpha-beta-rc convention for all pre-release version strings.** ADR-001's phase-to-version mapping is amended as follows:

| Phase | Original ADR-001 label | Amended version-line mapping |
|---|---|---|
| Phase A — reset, plugin infrastructure, per-feature plugins | "v0.9.0-preview" | `0.9.0a1` … `0.9.0aN` (alpha series; iterates per Phase A publish) |
| Phase B — hardened core, capability redesign, federation hardening, operator soak | "v0.9.x" (unlabeled) | `0.9.0b1` … `0.9.0bN` (beta series) |
| Phase C — v1.0 GA preparation | "v1.0.0-rc" | `1.0.0rc1` … `1.0.0rcN` (release-candidate series) |
| GA | "v1.0.0" | `1.0.0` |
| Phase D — post-1.0 expansion | "v1.x.y" | `1.0.1`, `1.1.0`, … (semver-standard) |

**The first build of stigmem is `v0.9.0a1`.**

### Per-ecosystem spelling

PEP 440 (Python) and semver (npm, Helm) use *different* spellings for the same release. PEP 440 permits the bare form `0.9.0a1`; semver requires a hyphen separator before any pre-release identifier (`MAJOR.MINOR.PATCH-prerelease`), so the same release in `package.json` is spelled `0.9.0-alpha.1`. This is not a contradiction — each ecosystem has its own canonical spelling for the same underlying release.

| Phase / class | PEP 440 (Python — `pyproject.toml`, PyPI) | Semver (Node — `package.json`, npm, Helm `appVersion`) | Shorthand for prose, ADRs, Git tags |
|---|---|---|---|
| Phase A alpha series | `0.9.0a1` … `0.9.0aN` | `0.9.0-alpha.1` … `0.9.0-alpha.N` | `v0.9.0a1` (PEP 440 spelling, brevity) |
| Phase B beta series | `0.9.0b1` … `0.9.0bN` | `0.9.0-beta.1` … `0.9.0-beta.N` | `v0.9.0b1` |
| Phase C release-candidate series | `1.0.0rc1` … `1.0.0rcN` | `1.0.0-rc.1` … `1.0.0-rc.N` | `v1.0.0rc1` |
| GA | `1.0.0` | `1.0.0` | `v1.0.0` |

**Single shorthand for prose.** Documentation, ADRs, blog posts, planning artifacts, GitHub release tags, and verbal communication use the **PEP 440 spelling** (`v0.9.0a1`, `v0.9.0b1`, `v1.0.0rc1`) as the single shorthand. It is shorter than the semver form, matches what `pip show stigmem` returns, and prevents drift between docs that reference the same release with two different strings. The semver-spelled form only appears in artifacts that npm / Helm parse.

**Git tag convention.** Git tags use the shorthand: `v0.9.0a1`, `v0.9.0b1`, `v1.0.0rc1`, `v1.0.0`. A single tag identifies the release across both ecosystems even though the published artifacts have different version strings.

**Version-consistency CI.** The version-consistency check (per Phase A PR 0) treats the two spellings as equivalent for the same release. Implementation: a normalizer maps both `0.9.0a1` (PEP 440) and `0.9.0-alpha.1` (semver) to a canonical key (e.g. `0.9.0.alpha.1`) and asserts all version emitters reference the same canonical key. The script's allow-list — which surface uses which spelling — is **not embedded in this ADR**. See §Surface manifest below.

### Surface manifest

This ADR captures **policy** (the spelling rules, the normalizer, the immutability boundary, the shorthand convention). It deliberately does *not* embed the inventory of release surfaces.

The inventory lives in a separate YAML manifest that is the canonical source of truth for which surfaces stigmem publishes to or emits version strings on, and which spelling each surface uses:

- **Path:** `release/version-surfaces.yaml` (in the stigmem repo; lands during Phase A PR 0 alongside `scripts/check_version_consistency.py`).
- **Schema:** one entry per surface with the following fields:

  | Field | Required | Meaning |
  |---|---|---|
  | `id` | yes | Stable identifier, kebab-case (e.g. `pypi-stigmem`, `helm-app-version`, `stigmem-version-header`). |
  | `kind` | yes | `external-registry` \| `internal-protocol` \| `internal-build-artifact` \| `documentation`. Filters by audience-and-failure-mode class. |
  | `category` | yes | Domain classifier (e.g. `python-package`, `node-package`, `container-image`, `http-header`, `transparency-log`, `chart-metadata`, `prose`). Independent axis from `kind` — supports cross-cutting queries. |
  | `file` | conditional | File path relative to repo root. Required for surfaces backed by a file; omitted for protocol-only surfaces (e.g., HTTP headers defined by spec). |
  | `field` | conditional | Dotted field path within the file (e.g., `project.version`, `appVersion`). |
  | `spelling` | yes | `pep440` \| `semver` \| `shorthand`. Canonical spelling for this surface. |
  | `sort_authority` | yes | Which ordering rule applies (`pep440`, `semver`). Determines how the CI compares versions for this surface. |
  | `spec` | optional | Cross-reference to the ADR or spec section that defines this surface (e.g., `ADR-012` for HTTP headers, `ADR-016` for Rekor manifest). |
  | `notes` | optional | Free-text caveats (e.g., "ClawHub format conventions need confirming on first publish"). |
  | `retired` | optional | Date (YYYY-MM-DD) the surface was retired. **Tombstone, do not delete the row** — keeps audit history of every surface stigmem has ever shipped to. |

- **Two query axes.** `kind` and `category` are independent. `kind: external-registry` filters by audience (user-visible breaking-change failure mode); `category: container-image` filters by domain (Docker, GHCR, OCI). The CI script and operator tooling can use either or both.

- **Schema validator.** `scripts/validate_version_surfaces.py` (lands with the manifest in PR 0) enforces the schema, rejects unknown spellings, and asserts that every entry's spelling matches its sort_authority's rules.

### Adding a new release surface

When stigmem ships to a new registry, defines a new internal version-bearing surface, or starts emitting versions on a new file:

1. **No new ADR required if the spelling rule already exists.** Append an entry to `release/version-surfaces.yaml` using one of the existing `spelling:` values (`pep440`, `semver`, `shorthand`). Add a CI test fixture covering the new surface. Open a normal PR.
2. **New ADR amendment required if the spelling rule does *not* already exist.** A surface that uses CalVer, a registry with custom version semantics (e.g., date-suffix conventions), or any spelling that needs new normalizer logic requires an amendment ADR to extend this one. The amendment defines the new spelling rule; the manifest entry then references it.

This split keeps policy stable and inventory operational. The ADR doesn't need amendment every time we ship to a new registry. Future operators reading the corpus see the durable rules in this ADR and the current surface state in the manifest.

### Retiring a release surface

When stigmem stops publishing to a registry or removes an internal surface:

1. Set `retired: YYYY-MM-DD` on the entry. Keep the row.
2. Update the CI to skip the entry when checking current version consistency (it remains validated for schema correctness).
3. Document the retirement in the next CHANGELOG entry.

The tombstone preserves the audit trail of every surface stigmem has ever shipped to, which matters for incident response (e.g., "did v0.9.0a3 ship on the deprecated GHCR namespace?") and for reasoning about historical compatibility claims.

### Scope of replacement

Replace the literal string "0.9.0-preview" (and the `v`-prefixed form) with `0.9.0a1` / `v0.9.0a1` / `0.9.0-alpha.1` (per-ecosystem table above) throughout:

- `pyproject.toml`, root `package.json`, `sdks/stigmem-ts/package.json`
- All other version-emitting artifacts subject to the version-consistency CI check (per Phase A PR 0)
- Master checklist, retraction post, LIMITATIONS.md, MAINTAINERS.md
- `experimental/<feature>/STATUS.md` files
- `docs/`, `spec/`, `release-notes/`, `migration/`
- All Internal-Comms planning artifacts (mutable working documents)

**Excluded from the scope of replacement:**

- **Accepted ADRs (immutable).** ADR-001 and any other Accepted ADR that references the original `v0.9.0-preview` string keeps its body unchanged. The reverse-link convention — adding `**Amended by:** ADR-019 (DATE)` to the amended ADR's Status block as lifecycle metadata — is how readers reach the current convention without rewriting the historical record. Same pattern applies to any future amendment chain (e.g., ADR-011 retroactively gets `**Amended by:** ADR-017`).

### What "preview" continues to mean

"Preview" remains as a **descriptive category word**, not a version string. Acceptable uses:

- "0.9.0a1 is a preview release — the first build of stigmem, pre-stable." (Microsoft uses this pattern: "Windows 11 Insider Preview build 22631.x.")
- README, retraction post, blog posts, and marketing prose may say "preview" to convey the pre-stable nature of any 0.9.0a* or 0.9.0b* build.
- "Preview" must not appear as a version string in any artifact subject to version-consistency CI.

"Experimental" continues to refer to plugins under `experimental/<feature>/` per ADR-008 / ADR-011 / ADR-018; that usage is unaffected.

### Iteration semantics

Each Phase A PR that publishes a build increments the alpha number: `0.9.0a1` (first PR 0 publish), `0.9.0a2` (next publish), and so on. Phase A is not required to ship one build per PR; the team chooses publish cadence. The constraint is that any subsequent publish strictly increments the alpha counter.

The transition from alpha to beta marks Phase A → Phase B. The transition from beta to rc marks Phase B → Phase C. The transition from rc to no-suffix marks Phase C → GA. Each transition is a one-way ratchet: no version line ever rolls back from beta to alpha or from rc to beta.

### Tagging convention

Git tags use the `v` prefix: `v0.9.0a1`, `v0.9.0a2`, `v0.9.0b1`, `v1.0.0rc1`, `v1.0.0`. Version strings emitted by tooling (pyproject, package.json, OpenAPI) omit the `v` prefix.

## Consequences

### Positive

- **Ecosystem-native ordering.** Within each ecosystem, sort order is correct without configuration: PyPI sorts `0.9.0a1 < 0.9.0a2 < 0.9.0b1 < 1.0.0rc1 < 1.0.0`; npm sorts `0.9.0-alpha.1 < 0.9.0-alpha.2 < 0.9.0-beta.1 < 1.0.0-rc.1 < 1.0.0`. The normalizer-backed version-consistency CI maps both spellings of any given release to a single canonical key.
- **No normalization surprise within an ecosystem.** `pip show stigmem` returns the exact PEP 440 string written in `pyproject.toml`. `npm view stigmem version` returns the exact semver string written in `package.json`. Each ecosystem speaks its own dialect; nothing is silently rewritten at publish time.
- **Iteration is built in.** Multiple Phase A publishes don't require inventing a successor convention.
- **Pre-release exclusion is built in.** `pip install stigmem` (without `--pre`) skips alpha/beta/rc by default. `npm install stigmem` (without an explicit pre-release tag) skips them. Adopters who want pre-stable builds opt in explicitly.

### Negative

- **Rename pass across Internal-Comms.** ~37 files contain references to the old "preview" string. One sweep replaces them.
- **Marketing-language drift.** "v0.9.0-preview" was a usable shorthand. "v0.9.0a1" reads as a build identifier, not a release name. Compensate with descriptive prose ("the v0.9.0 alpha line", "preview release", "pre-stable build") in user-facing surfaces.

### Neutral

- ADR-001 is not edited. Per the immutability rule (`ADRs/DEFINITION.md`), Accepted ADRs document the decision made at the time and are not rewritten when later ADRs amend them. ADR-001's body continues to reference the literal string `v0.9.0-preview` as the historical record of what was decided. Readers reach the current convention by following the amendment chain — ADR-001's Status block carries an `**Amended by:** ADR-019 (DATE)` annotation (lifecycle metadata, not a body edit), and ADR-019 is authoritative for the phase-to-version mapping going forward. The same pattern applies to any other ADR amended by this one or by future amendment ADRs.

## Open questions

None. This amendment is mechanical: replace one literal string with another, and adopt iteration semantics that PEP 440 / semver already specify.

## Related

- ADR-001 (the amended decision)
- ADR-012 (version-aware feature exposure) — uses version strings as feature-gating keys; alpha/beta/rc strings are valid keys.
- ADR-013 (deprecation policy) — compatibility windows defined in version-string ranges; alpha/beta/rc fit cleanly.
- ADR-014 (compatibility matrix) — YAML source-of-truth uses ordered version strings; alpha/beta/rc preserve ordering.
