# Documentation Ownership

This file defines where recurring release, security, and evidence facts live.
It implements the ADR-005 rule that each topic has one canonical owner and the
ADR-018 rule that security documentation should use a hub-and-link model instead
of duplicating the same analysis across multiple files.

## Canonical Homes

| Information type | Canonical home | Other files may | Other files must not |
| --- | --- | --- | --- |
| Release user/operator impact | `CHANGELOG.md` | Summarize impact and link to detailed security or release docs | Reprint full audit, evidence, or advisory tables |
| Current security posture and advisory disposition | `SECURITY.md` | Link to evidence ledgers and threat-model risks | Duplicate path/test/PR evidence |
| Finding-level evidence | `docs/internal/security-evidence-registry-*.md` | Record PRs, paths, tests, dispositions, and publication state | Become the public advisory index |
| Enduring architectural risks | `spec/security/threat-model.md` | Register cross-cutting R-XX risks and link to per-feature analysis | Add every audit finding as a risk |
| Machine-checkable mitigated-risk evidence | `spec/security/evidence-registry.json` | Support validators for mitigated threat-model risks | Carry human narrative or release notes |
| Feature facts | `features/<feature-slug>/` | Project summaries into roadmap, release, security, changelog, protocol, compatibility, and public feature docs | Maintain parallel feature dossiers in root docs, public docs, release docs, or `experimental/` |
| Strategic roadmap | `ROADMAP.md` | Link to detailed release roadmaps and milestone execution | Become a per-issue task board or release-notes draft |
| Detailed release scope | `docs/internal/releases/<version>-roadmap.md` | Define release contracts, scope, exclusions, artifacts, evidence gates, and release-note candidates | Replace GitHub issues for live execution |
| Release readiness | GitHub issues, milestones, and `docs/docs/operators/release-readiness.md` | Feed tag-time checks and public/operator status summaries | Be manually mirrored in several prose trackers |
| Private or embargoed staging | `Internal-Comms/stigmem/security/drafts/` | Hold unpublished publication drafts | Preserve post-publication snapshots of public docs |
| Architecture decisions | `docs/adr/` | Be linked from IC and planning docs | Be duplicated under Internal-Comms after publication |
| Roadmap/release document format | `docs/internal/roadmap-standards.md` | Be linked from release docs and review checklists | Drift into undocumented local conventions |
| Feature record migration sequencing | `docs/internal/features/feature-record-migration.md` | Track PR slicing, pilot migrations, and transition validation | Amend ADR-020 or become the canonical feature record itself |

## Release Security Rule

For a security release:

1. `SECURITY.md` is the public disposition index.
2. `CHANGELOG.md` records the release-impact summary.
3. The dated evidence registry records proof and lineage.
4. The threat model changes only when a finding exposes an enduring
   architectural risk class.
5. Internal-Comms drafts are deleted or trimmed to still-embargoed residue in
   the same coordinated publication batch.

## Review Checklist

Before merging a docs PR that touches release, security, or evidence material:

- Identify the canonical owner for each fact being added.
- Replace duplicate prose with links to the canonical owner.
- For feature facts, update `features/<feature-slug>/` once the feature has
  migrated to the ADR-020 structure.
- Keep summaries short in non-owner files.
- If a public artifact graduated from Internal-Comms, cross-link the public PR
  and IC cleanup PR.
- Run the relevant evidence and docs validators named by the changed files.
