---
title: Experimental & Deferred Features
sidebar_label: Experimental & Deferred
sidebar_position: 5
audience: Operator
description: "Features deferred from v0.9.0a1 default install, planned for staged re-introduction per ADR-008."
---

# Experimental & Deferred Features

This page lists features that are **not in v0.9.0a1's default install**. They were part of pre-reset specs but are deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md) (v1 critical-path scope) and [ADR-011](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/011-cross-cutting-extraction.md) (plugin architecture). Each will return through the [ADR-008](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) five-gate process: threat-model delta, ADR, conformance vectors, 30-day external operator soak, and adopter migration story.

This is the public surface of `Internal-Comms/stigmem/plans/version-prioritization.md` — the living tracker that maps every deferred feature to its re-introduction phase and PR.

---

## Deferred protocol features

| Spec | Feature | Phase | PR |
|---|---|---|---|
| §17 | Memory garden — advanced ACL (admin/writer/reader role model) | Phase A | PR 4e |
| §18 | Source attestation (`entity_uri` binding, three modes, audit log) | Phase A | PR 4f |
| §20 | Recall graph (vector embeddings, BM25+ANN+graph BFS+MMR, memory cards) | Phase A | TBD |
| §21 | Lazy instruction discovery (boot stub, manifest, `recall_instruction` tool) | Phase A | PR 4a |
| §23 | RTBF tombstones (signed entity_uri+scope suppression, federation propagation) | Phase A | PR 4d |
| §24 | Time-travel queries (`as_of` parameter, append-only retraction log) | Phase A | PR 4c |
| — | Subscriptions / push federation | Deferred | TBD |

Note: §25 Content-addressed fact IDs (CIDs) **stays in core** per ADR-017 — CIDs are load-bearing for the storage immutability stack and prompt-injection trust boundary.

## Deferred auth & integration

| Feature | Phase | Notes |
|---|---|---|
| OIDC SSO integration | Phase A | New auth trust boundary, not threat-modeled adversarially yet |
| Multi-tenant isolation | Phase A (PR 4g) | Most complex plugin; default install is single-tenant |
| Fuzzy entity resolver | Deferred | Convenience feature, not on critical path |

## Deferred storage backends

| Feature | Phase | Notes |
|---|---|---|
| PostgreSQL backend | Deferred | Highest-priority candidate after SQLite operator-validates |
| libSQL / Turso backend | Deferred | Adds third-party trust dependency |

## Deferred adapters & integrations

`stigmem-openclaw` is the only adapter shipped at v0.9.0a1. The following are kept in the codebase but will not graduate until OpenClaw v0.9 validates the contract:

- Obsidian + Obsidian-plugin adapters
- Letta, Zep, Cognee, Gemini, OpenAI-tools, Paperclip adapters
- MCP host connectors (Cursor, Zed, Codex CLI, Continue.dev) — the underlying `stigmem-mcp` adapter is at `0.4.0` and not aligned to v0.9.0a1
- Curator dashboard (Next.js)

## Deferred SDKs

Only the Python SDK (`stigmem-py`) and TypeScript SDK (`@eidetic-labs/stigmem-ts`) ship at v0.9.0a1. The Go SDK is deferred until the Python SDK is operator-validated.

## Deferred deployment surfaces

Docker Compose is the only deployment surface in v0.9.0a1. Helm chart, Fly.io configs, systemd units, Grafana dashboards, and PaaS configs all defer.

## Deferred commercial / operational features

| Feature | Notes |
|---|---|
| Billing hooks | Commercial concern; belongs in hosted offering |
| Memory cards (synthesis) | Synthesis path; defer |
| Decay sweep | Cron-driven; can be disabled |
| Async lint/decay job APIs | Blocked on lint/decay graduation |

---

## What this means for adopters

If you read about a feature in an older blog post, AI-generated summary, or third-party integration guide that doesn't appear in the current docs sidebar, it is almost certainly on this list. The implementation generally exists in the codebase but is gated, off by default, or not graduation-ready. **Do not depend on deferred features in production workloads** — they will return only after passing the ADR-008 gates, and the wire format may change between now and then.

## Restoration tracking

When a deferred feature graduates, its docs are restored from `Internal-Comms/stigmem/plans/aspirational-future-versions/docs-archive/<feature-slug>/`. Each archived page carries frontmatter mapping it back to its original repo path so restoration is mechanical:

```yaml
archived_from: docs/docs/<original-path>
archived_at: 2026-05-09
v0_9_0a1_status: deferred
feature: <feature-slug>
restore_when: <Phase A PR-X | TBD>
manifest_ref: stigmem/plans/aspirational-future-versions/docs-manifest.md
```
