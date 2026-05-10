# docs/archive/snapshots — versioned-docs snapshots

This directory holds Docusaurus `versioned_docs/` snapshots that were configured as versioned releases but **never represented actual publicly-shipped versions of stigmem**. Per [ADR-001](../../adr/001-versioning.md) + [ADR-019](../../adr/019-amendment-to-adr-001-prerelease-version-strings.md), the canonical version line of stigmem begins at `v0.9.0a1` (2026-05-09); prior version *markers* labeled internal development checkpoints, not tagged releases.

The snapshots are preserved here per the master-checklist §4.3a binding preservation principle. URLs that pointed at `/v1.1/*` and `/v0.2/*` were redirected to a landing page explaining that those URLs were not real releases.

## Snapshots

### `version-v1.1/`

Configured as `lastVersion: 'v1.1'` in pre-reset Docusaurus config. The v1.1 release was never publicly tagged or shipped. Content was harvested where correct under v0.9.0a1 (e.g., Memory Garden as Stable, federation handshake content) before the snapshot moved here.

### `version-v0.2/`

Earlier evolutionary checkpoint snapshot. Content harvested where historically accurate (motivation, early concepts) before move.

## How to read these snapshots

- **They are read-only historical artifacts.** Do not edit them; do not link adopters to them as current docs.
- The current canonical docs are at `docs/docs/`.
- Each snapshot retains its original Docusaurus directory structure for reference.

## Cross-references

- [`docs/archive/`](../) — parent index; `superseded/` and `placeholder-pages/` siblings.
- [ADR-001](../../adr/001-versioning.md) — versioning, why v0.9.0a1 is the first build.
- [ADR-019](../../adr/019-amendment-to-adr-001-prerelease-version-strings.md) — pre-release version-string convention.
