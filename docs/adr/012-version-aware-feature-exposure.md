# ADR-012: Version-aware feature exposure

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** ADR-001 (versioning), ADR-005 (docs IA), ADR-008 (experimental gates), ADR-013 (deprecation policy), ADR-014 (compatibility matrix); `stigmem/analyses/docs-structure-review-2026-05-06.md`

---

## Context

The retracted v1.0 / v2.0 docs had no inline signal of feature stability or version-introduced state on most pages. A reader on `concepts/federation/federation-trust.md`, `security/mtls.md`, or `sdks/connectors/cursor.md` could not tell:

- When the feature was introduced.
- What stability tier it sits in.
- What spec section is normative for it.
- Which versions of the node, SDK, and adapter are required to use it.

The information existed scattered across `CHANGELOG.md`, `spec/CHANGELOG.md`, and the single `experimental-features.md` page. None of it was inline where readers actually looked.

The version-aware exposure pattern *did* exist on `spec/` pages — `**Status:** Stable (v1.0; v1.1 §2.8)` plus a `<details>Revisions</details>` accordion. The pattern was correct and sophisticated; it was just applied in only one directory.

Industry practice in the closest analogous projects:

- **Node.js** — every API page has a Stability header (deprecated/experimental/stable/legacy) and an "Added in" version line, plus a History table per API.
- **Kubernetes** — alpha/beta/stable maturity tiers baked into API names; per-version docs.
- **Python stdlib** — `New in version X.Y` / `Changed in version X.Y` / `Deprecated since version X.Y` inline blocks.
- **Stripe** — per-feature stability flags, opt-in beta header for unreleased API features, version pinning via header.
- **MDN** — compatibility tables on every API page.

The cost of inline annotations is real — every page audit, every release a sweep — but the alternative (readers parsing changelogs to know what they can rely on) creates trust friction that compounds over releases.

## Decision

Adopt a Node.js-style inline pattern with Stripe-style protocol-level versioning headers. Concretely:

### Frontmatter convention

Every concept, feature, SDK, operator, security, and spec page carries:

```yaml
---
stability: stable | beta | experimental | deprecated
since: 0.9.0-preview
applies_to_version: 0.9.0+
spec_section: §17 (optional, for spec-bound features)
removed_in: 2.0.0 (only on deprecated entries)
replacement: ./new-feature-page.md (only on deprecated entries)
---
```

### Stability tier values

| Value | Meaning |
|---|---|
| `stable` | Spec section normative. In production. Eval-covered. No breaking changes planned within the major version. |
| `beta` | Spec normative. Feature-flagged or in early adopters. Minor breaking changes possible before next major. |
| `experimental` | Implemented behind a flag. Spec section may be `draft`. Breaking changes expected. Use behind feature flag in production at your own risk. |
| `deprecated` | Marked for removal. Still operational; replacement available. See ADR-013 for removal timeline. |

The `planned` value used in `concepts/features.md` does not become a stability tier. Planned features live in `experimental/` or in `ROADMAP.md`; they don't have feature pages yet.

### `<Stability />` Docusaurus component

A custom React component renders a colored banner at the top of every feature page from frontmatter:

```tsx
<Stability level="experimental" since="0.9.0-preview" specSection="§21" />
```

Rendered as an inline alert with the stability label, the since-version, and (when applicable) a link to the spec section.

For deprecated features, the banner additionally surfaces `removed_in` and a link to the `replacement` page.

### Generalized revisions accordion

The pattern from spec pages — `<details><summary>Revisions before vX.Y: ...</summary>...</details>` — generalizes to any feature page that has version-introduced changes. When a page's content changes meaningfully across versions, prior text is preserved in a collapsed accordion sourced either from the page's own git history or from the canonical CHANGELOG entry.

Tooling: a small Docusaurus plugin that, given a page's frontmatter `since`, can render an "earlier text from version-N" accordion when the markdown source contains a `:::revisions vX.Y` directive.

### Stripe-pattern wire-format pinning

Two HTTP headers operate at the protocol level, parallel to the inline page-level annotations:

- **`Stigmem-Version: 0.9.0-preview`** — clients lock to a declared protocol version. Server honors it; future server versions stay backward-compatible to declared versions for at least one major release (per ADR-013 deprecation policy). Documented in spec §3 (Wire Format) and `Operate → Compatibility`.
- **`Stigmem-Beta: feature-name`** — clients opt into experimental wire-level features per-call. Equivalent to a server-side feature flag at the protocol level; lets clients opt in without server reconfiguration. Lists of supported beta names live at `/v1/.well-known/stigmem` in a `betas` field.

These map to Stripe's `Stripe-Version` and beta-gate headers and serve the same purpose: per-client stability isolation without forcing server-side state on every flag combination.

### CI validator

The `validate-audience` plugin extends to also validate:

- `stability:` is present on every page in `concepts/`, `sdks/`, `operators/`, `security/`, `spec/`.
- `since:` is present and matches the SemVer pattern.
- Values match the allowed enum (`stable | beta | experimental | deprecated`).
- `removed_in:` is present iff `stability: deprecated`.
- `replacement:` resolves to an existing page.

CI fails on any violation. New pages cannot land without correct stability metadata.

### Auto-generated experimental-features index

The standalone `experimental-features.md` page is replaced by an auto-generated landing under Build that lists every page in the docs with `stability: experimental`, sorted by spec section or by since-version. Hand-maintenance of the page is retired.

## Alternatives considered

**1. Per-page badges only, no protocol-level headers.** Considered. Page badges answer "what stability is this feature?" Headers answer "how do I lock my client to a version?" These are different questions and the protocol-level answer cannot live in docs alone — the wire format has to support it. The two work together; one without the other is incomplete.

**2. Full Stripe-style calendar versioning of the wire format (e.g., `2026-05-06`).** Rejected as too heavy for a v0.9.0-preview project. SemVer is sufficient until the project has API-surface complexity that warrants calendar versioning. Reconsider in Phase D / E if the federation surface grows breaking-change pressure that SemVer can't absorb.

**3. Separate stability site (e.g., `stability.stigmem.dev`).** Rejected. Splitting the stability story from the feature docs forces readers to context-switch. Inline is the right model — the badge is part of the feature's documentation, not a separate concern.

**4. Markdown badges instead of a React component.** Considered. Static markdown badges (e.g., `![Stable](https://img.shields.io/badge/stability-stable-green)`) work without JS. Rejected because the component carries dynamic behavior — linking to spec sections, looking up replacement pages from frontmatter — that markdown badges can't do. The component is a one-time cost; markdown badges would be a permanent maintenance tax.

**5. Source `since` from git history automatically.** Considered. Tools like `git-blame` can derive when a page first appeared. Rejected because git history reflects when the *page* was created, not when the *feature* was introduced — a feature shipped in v0.5 might have its docs page created in v0.9. Authors must declare `since` explicitly; CI can't infer it.

## Consequences

### What gets easier

- **Reader trust.** Every feature page tells the reader what stability tier they're looking at and when it became available. No external lookup required.
- **Stripe-style version pinning** lets clients adopt newer server versions at their own pace without breaking. Reduces upgrade friction.
- **Beta features ship faster.** With per-call opt-in via header, experimental wire features can be exposed to early adopters without a server-side feature-flag config burden.
- **Auto-generated experimental-features index** retires the hand-maintained page; one less surface to drift.

### What gets harder

- **Every page audit on every release.** Stability and `since` annotations are now part of release discipline. Master-checklist §8.6 captures this as cross-phase ongoing work.
- **Component implementation cost.** ~1 day for `<Stability />` + frontmatter validator + auto-gen index. Ongoing maintenance: minimal, but the plugin tests are part of the docs CI.
- **Protocol-level header support.** `Stigmem-Version` and `Stigmem-Beta` headers must be honored in the node implementation. This is a real implementation cost: ~2 days for the node, plus SDK pass-through, plus tests for backward-compatibility behavior across versions. Slot in master-checklist §5.x (Phase B).
- **Backfill cost.** ~117 existing pages need stability metadata. ~3 days of mechanical sweep work, lands in master-checklist §4.3a.

### New risks

- **R-VAFE-1: stability declarations rot.** A page marked `stable` may quietly become `beta` in practice if implementation drifts. Mitigation: stability-badge audit at every minor release (master-checklist §8.6); CI validator catches missing/invalid metadata but cannot detect semantic drift; quarterly drift check at the human-review level.
- **R-VAFE-2: `Stigmem-Version` pinning creates implementation tail.** Supporting older protocol versions indefinitely accumulates code complexity. Mitigation: ADR-013 deprecation policy bounds this to one major version of support after deprecation; older pinned versions hard-fail with explicit error after that.
- **R-VAFE-3: `Stigmem-Beta` headers grow without bound.** If every experimental wire feature gets a beta header that lives forever, the protocol surface bloats. Mitigation: beta-graduation process — when an experimental feature reaches `stable` per ADR-008 gates, the beta header retires (returns `410 Gone`) and the feature is just part of the protocol; client-side use of the beta name produces a deprecation warning header.

## Implementation plan

Lands in master-checklist §4.3a (PR 2.5 — Docs site restructure and reversion sweep) as the docs-side adoption. Protocol-level header support lands in Phase B (master-checklist §5.x). Detailed task list:

- Add `<Stability />` Docusaurus component under `docs/src/components/`.
- Extend `validate-audience` plugin to also validate `stability:`, `since:`, `applies_to_version:`, `removed_in:`, `replacement:`.
- Backfill stability frontmatter on every page in `concepts/`, `sdks/`, `operators/`, `security/`, `spec/`.
- Generalize the `<details>Revisions</details>` accordion pattern; document the `:::revisions vX.Y` directive convention.
- Replace `experimental-features.md` with an auto-generated index page.
- Add `Stigmem-Version` and `Stigmem-Beta` header support to the node (Phase B).
- Add SDK pass-through of both headers (Phase B).
- Add `betas` field to `/v1/.well-known/stigmem` response (Phase B).
- Document headers in spec §3 Wire Format and `Operate → Compatibility`.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*