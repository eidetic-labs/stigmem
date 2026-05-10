# archive/ — repo-root archive for non-canonical artifacts

This directory holds artifacts that are preserved as part of the v0.9.0a1 reset per ADR-009 §11 + master-checklist §4.3a binding preservation principle, but are NOT part of the canonical docs site, code, or build.

## Contents

- `devto-lazy-discovery-tokenomics.md` — externally-published dev.to post (moved from `dogfood/` per PR 3 / ADR-009 §11). Preserved at repo root rather than `docs/blog/archive/` because the Docusaurus blog plugin processes everything under `docs/blog/` as a real blog post; this archive lives outside that tree to avoid forcing the post into the build pipeline.

## How to read this directory

Files here are read-only historical artifacts. Do not edit; do not link adopters here as current docs. The current canonical surfaces are:

- [`README.md`](../README.md) — repo entry point
- [`CHANGELOG.md`](../CHANGELOG.md) — current changelog
- [`ROADMAP.md`](../ROADMAP.md) — public roadmap
- [`docs/docs/`](../docs/docs/) — Docusaurus content (canonical docs site)
- [`docs/archive/`](../docs/archive/) — Docusaurus-tree archive (snapshots, superseded, placeholder pages)
