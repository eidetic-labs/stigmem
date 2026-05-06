---
title: Features
sidebar_label: Features
sidebar_position: 1
description: What Stigmem can do today — feature status table for evaluators, integrators, and operators.
---

# Features

*Audience: anyone evaluating, integrating, or operating Stigmem.*

Stigmem is an open, federated knowledge protocol — a layer where AI agents and humans store typed, traceable facts that travel across tools, platforms, and organizations. Each fact is an immutable record `(entity, relation, value, source, timestamp, confidence, scope)` written once, queryable forever, with full provenance and a defined expiry.

---

## How to read this page

| Status         | Meaning                                                                    |
|----------------|----------------------------------------------------------------------------|
| **Stable**     | Spec section normative. In production. Eval-covered. No breaking changes planned. |
| **Beta**       | Spec normative. Feature-flagged or in early adopters. Minor breaking changes possible before next major. |
| **Experimental** | Implemented behind a flag. Spec section is `draft`. Breaking changes expected. |
| **Planned**    | Spec draft exists. Not yet implemented.                                    |

This page does not show calendar dates. Stigmem ships when ready, not on a quarter boundary. To follow what's currently in flight, see [What's coming next](#whats-coming-next) below.

> **Why pick Stigmem over a vector-RAG product?** Stigmem retrieves *typed atomic facts*, not opaque chunks. Each embedding has an explicit `(entity, relation, value)` contract. Recall is hybrid (lexical + dense + graph) with provenance preserved end-to-end, and a memory-card fast path that 80–90% of recalls hit. Read the full deep-dive in the [Recall guide](../concepts/recall/recall.md).

---

## Core memory model

| Capability                          | Status     | Spec      | Docs                                   |
|-------------------------------------|------------|-----------|----------------------------------------|
| Immutable typed facts (entity, relation, value, source, timestamp, confidence, scope) | Stable | §2, §3    | [Asserting facts](../concepts/facts/asserting-facts.md) |
| Scope enforcement (`local` / `team` / `company` / `public`) | Stable | §3.5      | [Scope propagation](../concepts/federation/scope-propagation.md) |
| Confidence + decay (`valid_until`, retraction) | Stable | §15       | [Decay guide](../concepts/lifecycle/decay.md) |
| Synthesis (confidence-weighted current state) | Stable | §16       | [Synthesis guide](../concepts/lifecycle/synthesis.md) |
| Conflict surfacing & resolution     | Stable     | §6.3      | [Conflict resolution](../concepts/facts/conflict-resolution.md) |
| Entity naming rules                 | Stable     | §2.5–§2.6 | [Asserting facts](../concepts/facts/asserting-facts.md) |
| Lint semantics                      | Stable     | §14       | [Conformance](../build/guides/conformance.md) |
| Content-addressed fact IDs (CID)    | Stable     | §25       | [Content addressing](../build/guides/content-addressing.md) |
| Time-travel / `as_of` queries       | Stable     | §24       | [Time-travel](../build/guides/time-travel.md) |
| Right-to-be-forgotten (tombstones)  | Stable     | §23       | [RTBF](../build/guides/rtbf.md) |

## Recall, graph, and cards

| Capability                          | Status     | Spec   | Docs                                |
|-------------------------------------|------------|--------|-------------------------------------|
| `POST /v1/recall` hybrid pipeline (lexical + dense + graph) | Stable | §20.3  | [Recall guide](../concepts/recall/recall.md) |
| Vector embeddings (sqlite-vec, nomic-embed-text-v1.5 default) | Stable | §20.2  | [Embeddings](../build/guides/embeddings.md) |
| Graph adjacency index (`GET /v1/graph/neighbors`) | Stable | §20.1  | [Recall guide](../concepts/recall/recall.md) |
| Memory cards (stale-on-write, refresh-on-read) | Stable | §20.4  | [Memory cards](../build/guides/memory-cards.md) |
| Subscriptions (webhook + wake)      | Stable     | §20.5  | [Subscriptions](../build/guides/subscriptions.md) |
| Causal links (`derived_from`)       | Stable     | §20.6  | [Recall guide](../concepts/recall/recall.md) |

## Federation

| Capability                          | Status     | Spec   | Docs                                |
|-------------------------------------|------------|--------|-------------------------------------|
| Two-node federation (Ed25519 handshake, HLC cursors) | Stable | §6     | [Federation guide](../concepts/federation/federation.md) |
| Pull replication                    | Stable     | §6     | [Federation setup](../operate/runbooks/federation-setup.md) |
| N-node soak (4-node topology)       | Stable     | §6.7–§6.8 | [4-node federation](../concepts/federation/federation-4node.md) |
| Cross-org capability tokens         | Stable     | §19    | [Federation Trust](../concepts/federation/federation-trust.md) |
| Org manifests + transparency log    | Stable     | §19    | [Federation Trust](../concepts/federation/federation-trust.md) |
| Source-trust score & quarantine garden | Stable  | §19    | [Federation Trust](../concepts/federation/federation-trust.md) |
| Recall-time content sanitizer       | Stable     | §19    | [Federation Trust](../concepts/federation/federation-trust.md) |
| mTLS for peer connections           | Stable     | §22.1  | [mTLS](../security/mtls.md) |

## Storage & persistence

| Capability                          | Status     | Spec | Docs                                  |
|-------------------------------------|------------|------|---------------------------------------|
| SQLite backend                      | Stable     | —    | [Backends](../operate/backends/index.md) |
| libSQL backend (Turso-compatible)   | Stable     | —    | [Backends](../operate/backends/index.md) |
| Postgres backend (with pgvector)    | Beta       | —    | [Backends](../operate/backends/index.md) |
| SQLCipher at-rest encryption        | Stable     | —    | [Encryption at rest](../build/guides/encryption-at-rest.md) |
| Signed snapshot backup + PITR       | Stable     | —    | [Backup / restore](../operate/runbooks/backup-restore.md) |
| Cursor-checkpoint export/import     | Stable     | §6.6 | [Cursor reset recovery](../operate/runbooks/cursor-reset-recovery.md) |

## Trust, safety & operations

| Capability                          | Status     | Spec   | Docs                                |
|-------------------------------------|------------|--------|-------------------------------------|
| API-key authentication (per-scope)  | Stable     | §3.5   | [Authentication](../build/guides/authentication.md) |
| Source attestation                  | Stable     | §18    | [Source attestation](../build/guides/source-attestation.md) |
| Audit log (13 event types)          | Stable     | §22.3  | [Audit & quotas](../security/audit-and-quotas.md) |
| Per-principal token-bucket quotas   | Stable     | §22.4  | [Audit & quotas](../security/audit-and-quotas.md) |
| Ed25519 key rotation (dual-trust)   | Stable     | §22.2  | [Key rotation](../security/key-rotation.md) |
| Container hardening (distroless, seccomp, non-root) | Stable | §22.6 | [Container hardening](../security/container-hardening.md) |
| OIDC / SSO                          | Beta       | —      | [OIDC SSO](../build/guides/oidc-sso.md) |
| Multi-tenancy                       | Beta       | —      | [Multi-tenancy](../build/guides/multi-tenancy.md) |
| Right-to-be-forgotten (legal hold)  | Stable     | §23    | [RTBF](../build/guides/rtbf.md) |

## Gardens & curation

| Capability                          | Status       | Spec | Docs                                  |
|-------------------------------------|--------------|------|---------------------------------------|
| Memory Garden partitions (admin/writer/reader ACL) | Stable | §17 | [Memory gardens](../build/guides/memory-gardens.md) |
| Quarantine garden (untrusted writes review) | Stable | §19 | [Federation Trust](../concepts/federation/federation-trust.md) |
| Curator dashboard prototype         | Experimental | §17  | [Memory gardens](../build/guides/memory-gardens.md) |

## Agent integration

| Capability                          | Status     | Docs                                   |
|-------------------------------------|------------|----------------------------------------|
| MCP adapter (TypeScript)            | Stable     | [MCP / Claude Code](../sdks/connectors/index.md) |
| OpenClaw / Claude Code adapter      | Stable     | [OpenClaw](../sdks/connectors/openclaw.md) |
| Paperclip hook adapter              | Stable     | [Paperclip](../sdks/connectors/paperclip.md) |
| Cursor connector                    | Stable     | [Cursor](../sdks/connectors/cursor.md) |
| Zed connector                       | Stable     | [Zed](../sdks/connectors/zed.md) |
| Codex CLI connector                 | Stable     | [Codex CLI](../sdks/connectors/codex-cli.md) |
| Continue.dev connector              | Stable     | [Continue.dev](../sdks/connectors/continue-dev.md) |
| Gemini connector                    | Stable     | [Gemini](../sdks/connectors/gemini.md) |
| Ollama / LiteLLM connector          | Stable     | [Ollama / LiteLLM](../sdks/connectors/ollama-litellm.md) |
| Obsidian vault adapter (CLI/daemon) | Stable     | [Obsidian](../sdks/connectors/obsidian.md) |
| Obsidian community plugin           | Stable     | [Obsidian plugin](../sdks/connectors/obsidian-plugin.md) |
| Zep adapter                         | Stable     | [Zep](../sdks/connectors/zep.md) |
| Lazy instruction discovery          | Stable     | [Lazy instructions](../build/guides/lazy-instructions.md) |

## SDKs & tooling

| Capability                          | Status     | Docs                                |
|-------------------------------------|------------|-------------------------------------|
| Python SDK (`stigmem-py`)           | Stable     | [Python SDK](/docs/build/sdks/python) |
| TypeScript SDK (`stigmem-ts`)       | Stable     | [TypeScript SDK](../build/sdks/typescript.md) |
| Go SDK (`stigmem-go`)               | Stable     | [Go SDK](../build/sdks/go.md) |
| Conformance test suite              | Stable     | [Conformance](../build/guides/conformance.md) |
| Eval harness (79 adversarial + 400 recall probes) | Stable | [Eval harness](../operate/observability/eval-harness.md) |

## Observability

| Capability                          | Status     | Docs                                |
|-------------------------------------|------------|-------------------------------------|
| Prometheus metrics (8 counters / 3 histograms / 2 gauges) | Stable | [Observability](../operate/observability/index.md) |
| OpenTelemetry traces                | Stable     | [Observability](../operate/observability/index.md) |
| Grafana dashboards                  | Stable     | [Observability](../operate/observability/index.md) |
| Cost calculator                     | Stable     | [Cost calculator](../operate/cost-calculator.md) |

## Deployment

| Recipe                              | Status     | Docs                                |
|-------------------------------------|------------|-------------------------------------|
| Docker Compose                      | Stable     | [Deploy runbooks](../operate/runbooks/deploy-runbooks.md) |
| Helm / Kubernetes                   | Stable     | [Helm](../operate/deployment/helm.md) |
| Fly.io                              | Stable     | [Deploy runbooks](../operate/runbooks/deploy-runbooks.md) |
| systemd / bare metal                | Stable     | [Deploy runbooks](../operate/runbooks/deploy-runbooks.md) |
| PaaS one-pagers (Render / Railway / App Runner / Cloud Run) | Stable | [Deploy runbooks](../operate/runbooks/deploy-runbooks.md) |

## Spec v2.0 — in flight

| Capability                          | Status     | Spec                |
|-------------------------------------|------------|---------------------|
| §19 Federation Trust → confirm normative | Planned | v2.0 tag         |
| §20 Recall & Graph → normative      | Planned    | v2.0 tag            |
| Instruction-manifest pattern → normative | Planned | v2.0 tag         |
| Source-trust model → normative      | Planned    | v2.0 tag            |
| Migration guide v1.0 → v2.0         | Planned    | v2.0 tag            |

---

## What's coming next {#whats-coming-next}

The two next milestones, in order:

1. **Spec v2.0 tag** — closes federation-trust, recall, instruction-manifest, and source-trust as normative; ships the migration guide.
2. **Curator dashboard GA** — promotes the §17 dashboard from Experimental to Beta; first external connector demo using Source Attestation.

Anything beyond these two milestones is in spec drafts under the [Spec section](.../spec/index.md) and is subject to scope changes.

---

## Out of scope — explicit non-targets

- **A hosted/SaaS Stigmem product.** Reference deployments only; operators run their own nodes.
- **A competing agent runtime** to OpenClaw / Claude Code / LangChain etc.
- **A multi-agent orchestration layer.** Stigmem is a memory substrate — it makes existing agent frameworks, IDEs, and workflow tools more capable, not redundant.
- **An in-house GRC / compliance product.** Stigmem provides provenance primitives; compliance application logic is out of scope.
- **A vertical agent product** (support agent, bookkeeping agent, etc.) until post-v2.0.
- **A chatbot of any kind.**

---

*The previous State of Stigmem and Roadmap pages have been retired in favour of this single source of truth.*
