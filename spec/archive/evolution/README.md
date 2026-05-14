# spec/archive/evolution — evolutionary spec snapshots

This directory holds evolutionary snapshots of the stigmem protocol specification at successive development checkpoints (`v0.2` through `v2.0`). Per [ADR-001](../../../docs/adr/001-versioning.md): the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09); the version *markers* on these snapshots labeled internal development checkpoints, not tagged releases.

The spec *content* under each marker is real protocol specification — it was reviewed section-by-section against the actual implementation in `node/` during master-checklist §4.3a "Spec review and canonicalization to v0.9.0a1" and migrated forward into `spec/stigmem-spec-v0.9.0a1.md` (the canonical spec). These snapshots are preserved as the development record showing how the spec grew over time.

Each snapshot retains a header note pointing at the canonical v0.9.0a1 equivalent and the ADR-010 modular navigation entry point for cross-reference.

## Snapshots

| File | Captured at checkpoint | Status |
|---|---|---|
| `stigmem-spec-v0.2.md` | (early evolutionary checkpoint) | Archived |
| `stigmem-spec-v0.3-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v0.4-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v0.5-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v0.6-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v0.7-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v0.8-draft.md` | Draft checkpoint | Archived |
| `stigmem-spec-v1.0.md` | (retracted-label checkpoint) | Archived |
| `stigmem-spec-v1.1-draft.md` | (retracted-label draft) | Archived |
| `stigmem-spec-v2.0.md` | (retracted-label checkpoint; most complete pre-reset content) | Archived |

## How to read these snapshots

- **They are read-only historical artifacts.** Do not edit them; do not cite them as normative.
- The canonical spec is at `spec/stigmem-spec-v0.9.0a1.md`.
- Each snapshot has a banner at the top noting it is superseded and pointing to `spec/PROTOCOL.md`.
- For per-section provenance ("what did §17 say in v0.5 vs v1.0?"), this directory is the source.

## Why "evolution" and not "drafts" or "design history"

These files are not drafts — they captured what the spec said at each step. They are not design history of an archived project — the spec grew and continues to grow. "Evolution" is the framing in ADR-009 §8 + master-checklist §4.3a: development checkpoints in a continuously-evolving specification.

## Cross-references

- [`spec/stigmem-spec-v0.9.0a1.md`](../../stigmem-spec-v0.9.0a1.md) — canonical spec; the destination for all forward-migrated content.
- [`spec/EVOLUTION.md`](../../EVOLUTION.md) — protocol-spec evolution-history changelog (renamed from `spec/CHANGELOG.md` per master-checklist §4.3a).
- [ADR-001](../../../docs/adr/001-versioning.md) — versioning, why v0.9.0a1 is the first build.
- [ADR-010](../../../docs/adr/010-modular-specs.md) — modular per-topic specs (Phase B work; supersedes the monolithic spec model these snapshots reflect).
