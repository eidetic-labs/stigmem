# Plugin Publication Disposition

**Status:** active maintainer tracker
**Applies to:** adapter, tooling, dashboard, evaluation, and deployment helper
surfaces considered during the plugin publication readiness track
**Last updated:** 2026-05-25

This tracker classifies non-security-sensitive adapter and tooling surfaces for
the plugin publication readiness milestone. It does not publish artifacts,
create package promises, or graduate any feature under ADR-008.

> **Note:** This disposition table classifies adapter, tooling, dashboard,
> evaluation, and deployment surfaces. The six security-sensitive plugins
> (`source-attestation`, `multi-tenant`, `memory-garden-acl`, `tombstones`,
> `time-travel`, and `lazy-instruction-discovery`) are the primary publication
> queue and are tracked separately in
> [`plugin-publication-dry-run.md`](plugin-publication-dry-run.md). Both tracks
> must complete before any first publication clearance.

## Disposition Rules

| Disposition | Meaning | Registry action |
| --- | --- | --- |
| `publish-now` | Meets the plugin publication contract and has maintainer clearance. | May move to Goal 5 dry-run and publication clearance. |
| `hold` | Real implementation/package surface exists, but release-line validation is incomplete. | Do not publish until the named gaps close. |
| `defer` | Not a standalone plugin publication target for the active track. | Do not publish in this milestone. |

The MCP adapter is classified as `publish-now` after maintainer clearance for
the scoped npm package and independent `0.1.0` version line. Other adapter,
tooling, dashboard, evaluation, and deployment helper surfaces remain outside
the publication queue.

## Adapter and Tooling Order

| Order | Surface | Feature record | Implementation | Disposition | Missing validation before publication |
| --- | --- | --- | --- | --- | --- |
| 1 | MCP adapter | `features/mcp-adapter/` | `adapters/mcp/`; `experimental/mcp-adapter/` connector guides | `publish-now` | Scoped npm package `@eidetic-labs/stigmem-mcp@0.1.0`; package metadata, live protocol smoke, adapter security regressions, dry-run evidence, Codex CLI / Claude Code host UI smoke, Gemini CLI smoke with caveat, and maintainer clearance are complete. Continue.dev, Cursor, and Zed remain experimental/unvalidated connector guides, not publication blockers for `0.1.0`. |
| 2 | Obsidian adapter | `features/obsidian-adapter/` | `experimental/obsidian-adapter/cli/`; `experimental/obsidian-adapter/plugin/` | `hold` | Validate CLI package and Obsidian plugin packaging; run live-vault sync smoke; review key-storage guidance; decide registry/channel ownership. |
| 3 | Cognee adapter | `features/cognee-adapter/` | `experimental/cognee-adapter/` | `defer` | Assign owner; validate against a known Cognee runtime, vector store, and dependency set; refresh package metadata before reconsidering publication. |
| 4 | Letta adapter | `features/letta-adapter/` | `experimental/letta-adapter/` | `defer` | Assign owner; validate against a real Letta server and agent memory; refresh dependency/package compatibility. |
| 5 | Zep adapter | `features/zep-adapter/` | `experimental/zep-adapter/` | `defer` | Assign owner; validate against Zep Cloud or self-hosted Zep; refresh dependency/package compatibility. |
| 6 | Gemini adapter | `features/gemini-adapter/` | `experimental/gemini-adapter/` | `defer` | Assign owner; validate against a real Gemini API/model; refresh SDK/API compatibility and package metadata. |
| 7 | OpenAI-compatible tools adapter | `features/openai-tools-adapter/` | `experimental/openai-tools-adapter/` | `defer` | Assign owner; validate live LiteLLM, OpenAI SDK, and local Ollama paths; pin optional provider dependency compatibility. |
| 8 | Paperclip adapter | `features/paperclip-adapter/` | `experimental/paperclip-adapter/` | `defer` | Define an install artifact; add automated tests; run live Paperclip validation; review delegated-agent write policy and credential scope. |

## Non-Plugin Tooling and Deployment Surfaces

| Surface | Feature record | Implementation | Disposition | Reason |
| --- | --- | --- | --- | --- |
| Dashboard | `features/dashboard/` | `experimental/dashboard/` | `defer` | Internal/deployment surface, not a standalone plugin artifact; live-node, auth/session, dependency, and deployment posture gates remain open. |
| Evaluation harness | `features/eval-harness/` | `experimental/eval-harness/` | `defer` | Concept-only in the current repository state; no runnable harness/corpus package exists. |
| Fly.io deployment helper | `features/deploy-fly/` | `experimental/deploy-fly/` | `defer` | Deployment recipe, not plugin artifact; live deployment, persistence/restore, secrets, and dashboard validation remain open. |
| PaaS deployment helper | `features/deploy-paas/` | `experimental/deploy-paas/` | `defer` | Deployment recipes, not plugin artifacts; live platform, persistence, secrets, scaling, and cost validation remain open. |
| systemd deployment helper | `features/deploy-systemd/` | `experimental/deploy-systemd/` | `defer` | Deployment helper, not plugin artifact; live distro, hardening, upgrade/rollback, and offline-install validation remain open. |
| Helm deployment helper | `features/deploy-helm/` | `experimental/deploy-helm/` | `defer` | Deployment chart, not plugin artifact; chart publication, live cluster, hardening, and upgrade validation remain open. |
| Grafana deployment helper | `features/deploy-grafana/` | `experimental/deploy-grafana/` | `defer` | Observability seed material, not plugin artifact; live stack, metric contract, alert review, and packaging guidance remain open. |

## Goal 5 Inputs

Only `hold` surfaces may be reconsidered in Goal 5 after a follow-up PR closes
their missing validation. A surface may move from `hold` to `publish-now` only
when its feature record records:

- package metadata and registry/channel ownership
- install and uninstall instructions
- live integration smoke evidence
- security review for credentials, host integration, and write surfaces
- maintainer clearance for a specific registry action

Deferred surfaces remain discoverable in feature records and public
experimental docs, but they are not part of the active publication queue.
