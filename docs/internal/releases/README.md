# Internal Release Roadmaps

This directory is the canonical home for detailed Stigmem release roadmaps.

`ROADMAP.md` preserves the strategic horizon. Files in this directory define
the concrete release contract for one release or release horizon: what is in
scope, what is out of scope, what artifacts ship, what evidence gates the
release, and what becomes release notes.

Use the format defined in
[`../roadmap-standards.md`](../roadmap-standards.md#internal-release-roadmap-standard).

## Index

| Release | Status | Purpose |
| --- | --- | --- |
| [`v0.9.0a1`](./v0.9.0a1-roadmap.md) | Historical | First-build release record and posture reset. |
| [`v0.9.0a2`](./v0.9.0a2-roadmap.md) | Historical | Artifact-refresh, extraction, and security-publication record. |
| [`v0.9.0a3`](./v0.9.0a3-roadmap.md) | Active | Current alpha release contract. |

## Rules

- Historical release roadmaps record what was intended, what shipped, and what
  was deferred.
- Active release roadmaps define the release contract but link to GitHub issues
  and milestones for live execution.
- Future release roadmaps may exist before a milestone opens, but must be marked
  `future gate` or `planned`.
- Do not duplicate ADR text. Link to ADRs and describe the release consequence.
- Do not duplicate full security evidence. Link to `SECURITY.md`, dated evidence
  registries, and threat-model evidence as appropriate.
