# ADR-014: Compatibility matrix

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** ADR-001 (versioning), ADR-005 (docs IA), ADR-012 (version-aware feature exposure), ADR-013 (deprecation policy); `stigmem/analyses/docs-structure-review-2026-05-06.md`

---

## Context

Stigmem's surface is multi-package: a node, a Python SDK, a TypeScript SDK, a Go SDK, an MCP adapter, an OpenClaw adapter, plus a growing catalog of host connectors (Cursor, Zed, Codex CLI, Continue Dev, Gemini, Ollama-LiteLLM, Paperclip, Obsidian, Zep). Each ships its own version. The protocol itself is versioned. None of the existing docs answer cross-package questions a real adopter has:

- "What's the minimum node version for the libSQL backend?"
- "Does Python SDK 0.x work against a v0.9.0-preview node?"
- "Does the Cursor MCP connector require any specific protocol section?"
- "Does the OpenClaw adapter v0.9 work with the TypeScript SDK 0.x?"
- "If I pin to `Stigmem-Version: 0.9.0-preview`, which SDK versions support that header?"

These are not edge cases — they are the first questions an integrator asks. Without a compatibility matrix, the answer is to read CHANGELOGs across multiple packages and infer.

Industry practice:

- **MDN browser compatibility tables** are the gold standard: a row per feature, columns per browser/version, marking the earliest version of each that supports the feature. Auto-generated from a `browser-compat-data` JSON source.
- **Kubernetes** ships a "Supported versions" page per release line, naming kubelet/kube-apiserver/etcd version compatibility windows.
- **AWS SDKs** maintain per-language SDK release notes that name minimum SDK versions for each new API.
- **Stripe** publishes API version compatibility per SDK in each SDK's docs.

The MDN model is the closest fit — feature-rich, generator-driven, auto-validated. Hand-maintained narrative compatibility prose drifts; a structured source-of-truth file with build-time rendering does not.

## Decision

A single source-of-truth YAML file at `docs/compatibility-matrix.yaml` declares compatibility relationships across packages. The file is committed; CI validates it against the actual published versions of each package; a Docusaurus plugin renders it as the `Operate → Compatibility` page (per ADR-005 IA placement).

### Source-of-truth schema

```yaml
# docs/compatibility-matrix.yaml
generated_for_protocol_version: 0.9.0-preview

packages:
  node:
    versions:
      - "0.9.0-preview"
    repository: github.com/eidetic-labs/stigmem
  python_sdk:
    name: stigmem-py
    versions:
      - "0.9.0-preview"
  typescript_sdk:
    name: stigmem-ts
    versions:
      - "0.9.0-preview"
  go_sdk:
    name: stigmem-go
    versions: []  # not shipped in v0.9.0-preview; experimental
  mcp_adapter:
    versions:
      - "0.9.0-preview"
  openclaw_adapter:
    versions:
      - "0.9.0-preview"

connectors:
  - id: cursor
    requires:
      mcp_adapter: ">=0.9.0-preview"
      cursor: ">=0.42"
  - id: openclaw
    requires:
      openclaw_adapter: ">=0.9.0-preview"
      openclaw: ">=1.2"
  # ... one entry per supported connector

features:
  - id: stigmem-version-header
    spec_section: §3.4
    requires:
      node: ">=0.9.0-preview"
      python_sdk: ">=0.9.0-preview"
      typescript_sdk: ">=0.9.0-preview"
    notes: "Wire-format pinning per ADR-012."
  - id: libsql-backend
    spec_section: §10
    stability: experimental
    requires:
      node: ">=0.9.0-preview"
    notes: "Storage backend trait; default backend is SQLite; alternative backends (libSQL, etc.) are opt-in plugins."
  - id: argon2id-key-hashing
    requires:
      node: ">=0.9.0-preview"
    notes: "Per ADR-007."
  # ... one entry per feature with cross-package coupling

protocol_compatibility:
  - protocol_version: "0.9.0-preview"
    supported_by:
      node: ">=0.9.0-preview"
      python_sdk: ">=0.9.0-preview"
      typescript_sdk: ">=0.9.0-preview"
    deprecation_window: "supported through 1.x; removable in 2.0 per ADR-013"
```

### Rendered output

The Docusaurus plugin renders three tables on the `Operate → Compatibility` page:

1. **Package versions table.** Rows: packages. Columns: latest stable, beta, experimental versions.
2. **Connector compatibility table.** Rows: connectors. Columns: stigmem-side (adapter version) and host-side (host application version) requirements.
3. **Feature compatibility table.** Rows: features. Columns: each package, with the version constraint (e.g., `>=0.9.0-preview`).

Each row links to the relevant feature page (using the spec_section reference where applicable).

### CI validation

A `scripts/check_compatibility_matrix.py` validator runs in CI:

- Every package version in `docs/compatibility-matrix.yaml` corresponds to an actual tagged release (or to `unreleased` with a banner).
- Every feature's `requires` entries reference packages that exist in the matrix.
- Every connector's `requires` entries reference packages that exist in the matrix.
- Every spec_section reference points to a real spec section.
- No version in the matrix is below the `since:` value of the corresponding feature page (cross-validation with ADR-012 frontmatter).

CI fails on any inconsistency. A docs PR cannot land if it changes a feature's `since` without updating the matrix; a release PR cannot ship without bumping the matrix.

### Update cadence

The matrix is updated as part of every release:

- **At deprecation:** matrix entry annotates the feature with `deprecated_since` and `removed_in` (per ADR-013).
- **At feature removal:** matrix entry moves to a `removed_features` section with a final compatibility window.
- **At new package release:** the new version appears in the `versions` list; cross-package compatibility for new features is declared.

A `make compatibility-matrix-check` target runs the validator locally so contributors can pre-flight matrix changes before pushing.

## Alternatives considered

**1. Hand-maintained narrative prose on each feature page.** Rejected. Compatibility prose drifts; a feature page maintained by one person can't capture the full multi-package picture without reading every other package's CHANGELOG. A structured source-of-truth removes the burden.

**2. Per-package compatibility sections, no central matrix.** Considered. Each package's docs declare what it works with. Rejected because the same compatibility claim ends up duplicated in N places — Python SDK page says "works with node 0.9.0+", node page says "works with Python SDK 0.9.0+" — and these will drift independently. The matrix is the deduplicated source.

**3. GitHub Releases as the source of truth.** Rejected. GitHub releases are good for binary distribution but bad for cross-package reading. An adopter shouldn't have to read 7 release pages to answer one question.

**4. MDN-style external `browser-compat-data` repo.** Considered. Hosting compatibility data in a separate repo is overkill at v0.9.0-preview. Reconsider if community contributions to compatibility data become a real workflow (probably v2.0+).

**5. Auto-generate matrix from package metadata (e.g., Python SDK declares `supports_protocol = "0.9.0-preview"` in `pyproject.toml`).** Considered as a future enhancement. Rejected as the *primary* mechanism for v0.9.0-preview because the metadata schema would need to land in every package, and the matrix's value is most useful before package-level metadata exists. The YAML source-of-truth ships first; package-metadata-driven generation is a future ADR if the manual matrix becomes a maintenance burden.

## Consequences

### What gets easier

- **Adoption planning.** Operators and integrators can answer "does X work with Y" from one page.
- **Release discipline.** The matrix update is a forcing function: a release PR has to think about compatibility explicitly.
- **Cross-package validation.** CI catches inconsistencies between feature pages, the matrix, and actual package versions.
- **Migration planning.** When a deprecation lands (per ADR-013), the matrix shows the support window across every package that touches the deprecated feature.

### What gets harder

- **Maintenance overhead per release.** Every release adds rows to the matrix. ~30 minutes of careful editing per release; non-trivial but bounded.
- **YAML hand-editing risk.** Hand-edited YAML is error-prone. Mitigation: CI validator catches structural errors; `make compatibility-matrix-check` for local pre-flight.
- **Initial population cost.** ~1 day to populate the matrix for v0.9.0-preview's release surface (master-checklist §4.3a or §5.x).

### New risks

- **R-CM-1: matrix drift from package reality.** A package ships a breaking change but the matrix still says it's compatible. Mitigation: CI validator cross-checks `since` declarations on feature pages; release-PR convention requires matrix update; quarterly drift check.
- **R-CM-2: over-promising compatibility.** A feature is declared compatible with a version that wasn't actually tested. Mitigation: matrix entries require evidence — at minimum, a passing CI run against the named version. For non-CI'd combinations (e.g., specific host application versions for connectors), the matrix annotates `tested: false` and a `last-verified: <date>` hint.
- **R-CM-3: matrix complexity outgrows the YAML format.** As the package surface grows, the YAML may become too unwieldy to hand-edit. Mitigation: monitor; if the file exceeds ~500 lines, factor into per-package YAML files imported into a root schema. Reconsider auto-generation from package metadata.

## Implementation plan

Lands in master-checklist §4.3a (PR 2.5 — Docs site restructure and reversion sweep) for the schema, validator, and rendered page. Initial population uses v0.9.0-preview as the only baseline version.

- Author the schema in `docs/compatibility-matrix.yaml` with v0.9.0-preview baseline.
- Add `scripts/check_compatibility_matrix.py` validator.
- Add Docusaurus plugin (or remark/rehype hook) that reads the YAML at build time and renders the three tables.
- Add `Operate → Compatibility` page using the rendered output.
- Add `make compatibility-matrix-check` target.
- Add CI step running the validator on every PR.
- Document the matrix in `CONTRIBUTING.md` (when to update, how to update).
- Wire matrix updates into the release runbook.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*