# Feature Records

Feature records are the canonical product record for Stigmem features. They
implement ADR-020 by making the feature, not the release, package, docs page, or
implementation directory, the binding unit for feature truth.

High-level documents such as `ROADMAP.md`, `CHANGELOG.md`, `SECURITY.md`,
`spec/PROTOCOL.md`, and public feature pages should summarize or project facts
from feature records instead of owning duplicate feature detail.

## Directory Contract

Every migrated feature lives at:

```text
features/<feature-slug>/
```

Feature slugs use lowercase kebab case and name the capability:

```text
features/content-addressed-ids/
features/federation-trust/
features/time-travel/
features/openclaw-adapter/
```

Do not encode maturity or implementation mode in the path. Use metadata for
that classification.

## Required Files

Every migrated feature directory must contain these files:

| File | Role |
| --- | --- |
| `README.md` | Overview, canonical metadata, owner, maturity, implementation paths, and links to the feature files. |
| `spec.md` | Normative feature behavior. |
| `status.md` | Lifecycle state, gate status, release history, and known gaps. |
| `evidence.md` | Implementation paths, tests, conformance vectors, validators, and coverage gaps. |
| `security.md` | Feature-specific threat model deltas, mitigations, residual risks, and advisory links. |
| `changelog.md` | Feature-local change history by release. |

If a file has no feature-specific content yet, state that explicitly. Missing
files are not used to mean "not applicable."

## Required Metadata

`README.md` must start with frontmatter:

```yaml
---
feature_id: time-travel
title: Time-travel queries
status: active
stability: experimental
since: 0.9.0a1
owner: maintainers
feature_type: plugin
default_surface: opt-in
canonical_spec: Spec-X3-Time-Travel-Queries
implementation_path: experimental/time-travel
package: stigmem-plugin-time-travel
adr_refs:
  - ADR-008
  - ADR-020
security_refs:
  - none
release_lines:
  - v0.9.0a1
---
```

Required scalar fields:

| Field | Requirement |
| --- | --- |
| `feature_id` | Unique lowercase kebab-case identifier. Should match the directory slug unless there is a documented compatibility reason. |
| `title` | Human-readable feature name. |
| `status` | One of `proposed`, `active`, `shipped`, `deferred`, `superseded`. |
| `stability` | One of `stable`, `beta`, `experimental`, `deprecated`. |
| `since` | First release line that introduced, proposed, or reserved the feature. Use `unreleased` for future proposals. |
| `owner` | Owning team or role. |
| `feature_type` | One of `core`, `plugin`, `adapter`, `sdk`, `deployment`, `protocol`, `tooling`, `docs`. |
| `default_surface` | One of `default`, `opt-in`, `experimental`, `internal`, `external`. |
| `canonical_spec` | Canonical spec identifier or `none`. Must be unique when present. |
| `implementation_path` | Primary implementation path or `none`. |

Recommended list fields:

| Field | Requirement |
| --- | --- |
| `adr_refs` | Related ADR identifiers, or `none`. |
| `security_refs` | Related threat-model risks, advisories, or `none`. |
| `release_lines` | Release lines that introduced or materially changed the feature. |

## Validation

Run the feature record validator from the repository root:

```bash
python3 scripts/check_feature_records.py
```

The validator currently checks migrated feature directories under `features/`
and skips `features/feature-template/`. This lets legacy feature documentation
migrate incrementally while enforcing the contract for every feature record that
has entered the new structure.

## Template

Use `features/feature-template/` when creating a feature record. Replace every
placeholder before the feature is considered migrated.
