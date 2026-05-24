# Plugin Publication Contract

**Status:** active maintainer standard
**Applies to:** standalone experimental Stigmem plugin artifacts
**Last updated:** 2026-05-23

This contract defines the minimum evidence required before a plugin source
package under `experimental/<feature>/` can be published as a standalone
artifact. It does not graduate a plugin, make it supported, or make it
default-on. ADR-008 graduation remains a separate future gate.

## Publication Classes

| Class | Meaning | Registry action |
| --- | --- | --- |
| `publish-ready` | The plugin satisfies this contract and has maintainer clearance. | May publish as an experimental artifact. |
| `hold` | The plugin is close, but one or more publication gates are missing. | Do not publish. |
| `defer` | The plugin is not intended for standalone artifact publication in the active track. | Do not publish. |

## Required Package Metadata

Every publish-ready plugin must have:

- a package name matching `stigmem-plugin-<feature-slug>` unless a compatibility
  reason is documented in the feature record
- a package version aligned with the release train being published
- a `stigmem.plugins` entry point that resolves to the plugin manifest
- a manifest with stable plugin id, hook registrations, capabilities,
  compatibility bounds, config schema, and health behavior
- README install, enable, disable, test, and uninstall instructions
- explicit experimental/stability language in package metadata and README
- license, authorship, and source repository metadata

## Required Feature Record State

The feature record under `features/<feature-slug>/` remains the source of
truth. Before publication, it must state:

- `feature_type: plugin` or another explicit plugin-adjacent type
- `stability: experimental`
- `default_surface: opt-in`, `external`, or another non-default value
- the implementation path under `experimental/<feature>/`
- the package name
- release lines that introduced and materially changed the plugin
- known gaps that block ADR-008 graduation
- publication state: `publish-ready`, `hold`, or `defer`

The six feature files must agree:

- `README.md` states package identity and stability.
- `spec.md` defines enabled behavior.
- `status.md` states lifecycle, gate status, and publication state.
- `evidence.md` names tests, build commands, and residual coverage gaps.
- `security.md` states threat-model deltas, mitigations, and residual risk.
- `changelog.md` records publication-relevant changes.

## Required Behavior Evidence

Every publish-ready plugin must prove both disabled and enabled behavior.

Disabled behavior evidence:

- default installs do not load or activate plugin behavior
- disabled config returns no-op, pass-through, or fail-closed decisions exactly
  as specified by the feature record
- missing config does not silently enable the plugin
- invalid config fails predictably and without partial activation

Enabled behavior evidence:

- enabled hooks execute on the intended surfaces
- hook ordering and capability checks match the manifest
- security-sensitive decisions are tested for allow, deny, and malformed input
- migrations are registered and idempotent when the plugin owns schema changes
- health/status signals report useful operator state without leaking secrets

## Required Security Evidence

Every publish-ready plugin must have a security disposition that covers:

- which threat-model risks it mitigates, contributes to, or leaves unchanged
- whether the plugin introduces new data disclosure, authorization, replay,
  isolation, or supply-chain risks
- how default-disabled behavior preserves core safety
- whether any Critical/High finding requires GHSA handling before publication
- whether Medium/Low findings are captured in `SECURITY.md` or receive a
  documented carve-out

If the plugin handles tenant isolation, source identity, tombstones,
authorization, federation, or instruction handling, the review must include
malformed input and cross-boundary tests before publication.

## Required Release Evidence

Before a plugin artifact is published, the maintainer must confirm:

- package build and install dry-runs pass from a clean checkout
- package metadata points to the exact source repository and commit/tag
- registry provenance is available where the registry supports it
- detached signatures or release assets are planned when the artifact is
  attached to a GitHub release
- release notes state the plugin remains experimental and opt-in
- rollback/yank instructions are documented for the registry used
- post-publish verification checks the registry artifact, install command,
  entry point discovery, and feature-record links

## Supply-Chain Attestation

Every Python plugin reaching `publish-ready` must satisfy these supply-chain
requirements:

- PyPI Trusted Publisher via GitHub Actions OIDC; do not publish with a
  long-lived PyPI API token.
- Sigstore signing for every wheel and source distribution publication, with
  the verification command recorded in the feature evidence record.
- CycloneDX or SPDX JSON SBOM generated for the release artifact and attached
  to the corresponding GitHub release or publication evidence.
- Dependency bounds that include appropriate upper limits for the release line;
  dependencies must not use open-ended `>=N` ranges without a documented
  compatibility reason.
- Reproducible build commands and SHA-256 hashes for wheel and source
  distribution artifacts recorded in feature evidence or changelog entries.

Every npm-distributed adapter reaching `publish-ready` must satisfy these
supply-chain requirements:

- `publishConfig.provenance: true` in `package.json`.
- Publication through GitHub Actions OIDC-backed npm provenance, not a
  long-lived npm token.
- Dependency ranges appropriate for the trust tier: exact pins for prerelease
  Eidetic Labs dependencies and reviewed major-version bounds for stable
  third-party dependencies.
- Dry-run output that records package contents, integrity, tag, access level,
  and rollback or deprecation instructions before publication.

## Publication Approval

Publication requires maintainer approval after the relevant goal issue closes.
Source package existence is not approval to publish. A plugin may remain
available in the repository as experimental source indefinitely without a
registry artifact.

## Validation

Run the relevant repo checks before requesting publication clearance:

```bash
uv run python scripts/check_feature_records.py
uv run python scripts/check_feature_projections.py
uv run python scripts/check_feature_security_projection.py
uv run python scripts/check_feature_changelog_projection.py
uv run python scripts/check_feature_compatibility_projection.py
uv run python scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

Per-plugin PRs must add focused package/build/test commands for the plugin
being moved to `publish-ready`.
