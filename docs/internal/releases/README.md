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
| [`v0.9.0a3`](./v0.9.0a3-roadmap.md) | Historical | CID validation and alpha artifact refresh. |
| [`v0.9.0a4`](./v0.9.0a4-roadmap.md) | Historical | Time-travel plugin-boundary validation and alpha artifact refresh. |
| [`v0.9.0 alpha series`](./v0.9.0-alpha-series-roadmap.md) | Planned | Detailed alpha deployment sequence, phase plan, and exit evidence. |
| [`future hardened core`](./future-hardened-core-roadmap.md) | Future gate | Preserved hardened-core plan; not an active beta milestone. |
| [`future RC / GA`](./future-rc-ga-roadmap.md) | Future gate | Preserved release-candidate and stable-release gates. |
| [`post-GA expansion`](./post-ga-expansion-roadmap.md) | Future gate | Preserved v1.x expansion and plugin stewardship horizon. |
| [`alpha extraction and graduation`](./alpha-extraction-and-graduation.md) | Maintainer reference | Alpha extraction process and ADR-008 graduation distinction. |

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
