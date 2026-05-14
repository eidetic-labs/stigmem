---
title: Experimental Features
sidebar_label: Experimental Features
sidebar_position: 5
audience: Operator
description: "Canonical public index of Stigmem features outside the v0.9.0a1 default surface, including Spec-X protocol features, adapters, SDKs, deployment recipes, and tooling."
---

# Experimental Features

This page lists features that exist outside the v0.9.0a1 default surface. Experimental
does not mean "almost stable": it means the feature is opt-in, unsupported for
production reliance, and must pass the ADR-008 reintroduction gates before it can
graduate into the supported surface.

Start with the [feature matrix](../concepts/features.md) for the supported v0.9.0a1
surface. Use this page when you need to inspect what was deferred, where it lives,
and whether it has a protocol spec.

## Status Model

| Status | Meaning |
|---|---|
| `Spec-XN` experimental protocol feature | Has real protocol/design substance and a colocated `experimental/<feature>/spec.md` source. Rendered spec pages live under the Specification section. |
| Experimental implementation surface | Has code, docs, deployment recipes, adapter code, SDK code, or operational tooling under `experimental/<feature>/`, but no protocol spec yet. The feature's `STATUS.md` is the tracking source. |
| Dormant | Preserved for future work, but no active ADR-008 gate progress. |
| Blocked | Cannot progress until another roadmap item lands first. |

Every experimental directory should carry a `STATUS.md`. A `Spec-XN` assignment is
reserved for protocol-bearing features; adapters, SDKs, dashboards, deployment
recipes, and tooling do not get fake specs unless they later define protocol
behavior.

## Protocol Features

These features have a `Spec-XN-*` experimental spec. They are not part of the
supported default install.

| Feature | Spec | Source | Status | Notes |
|---|---|---|---|---|
| Lazy instruction discovery | [`Spec-X1-Lazy-Instruction-Discovery`](../spec/experimental/lazy-instruction-discovery.md) | [`experimental/lazy-instruction-discovery/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/lazy-instruction-discovery) | Blocked | Requires ADR-003 capability redesign before reintroduction. |
| RTBF tombstones | [`Spec-X2-RTBF-Tombstones`](../spec/experimental/rtbf-tombstones.md) | [`experimental/tombstones/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/tombstones) | Dormant | Regulatory-impact feature; needs operator runbooks and adversarial federation coverage. |
| Time-travel queries | [`Spec-X3-Time-Travel-Queries`](../spec/experimental/time-travel-queries.md) | [`experimental/time-travel/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/time-travel) | Dormant | Coupled to tombstone/legal-hold semantics. |
| Memory Garden advanced ACL | [`Spec-X5-Memory-Garden-Advanced-ACL`](../spec/experimental/memory-garden-advanced-acl.md) | [`experimental/memory-garden-acl/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/memory-garden-acl) | Dormant | Basic scopes/gardens are stable; advanced ACL remains experimental. |
| Source attestation | [`Spec-X6-Source-Attestation`](../spec/experimental/source-attestation.md) | [`experimental/source-attestation/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/source-attestation) | Dormant | Extends provenance; reintroduction depends on hardened identity/key lifecycle. |
| Subscriptions | [`Spec-X7-Subscriptions`](../spec/experimental/subscriptions.md) | [`experimental/subscriptions/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/subscriptions) | Dormant | Push delivery waits for pull federation validation. |
| Intent envelope | [`Spec-X8-Intent-Envelope`](../spec/experimental/intent-envelope.md) | [`experimental/intent-envelope/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/intent-envelope) | Deferred indefinitely | Preserved design intent; no active reintroduction path. |
| Decay semantics | [`Spec-X9-Decay-Semantics`](../spec/experimental/decay-semantics.md) | [`experimental/decay/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/decay) | Dormant | Deferred memory-hygiene feature. |
| Synthesis | [`Spec-X10-Synthesis`](../spec/experimental/synthesis.md) | [`experimental/synthesis/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/synthesis) | Dormant | Deferred snapshot/commercial-path feature. |
| Recall graph | [`Spec-X11-Recall-Graph`](../spec/experimental/recall-graph.md) | [`experimental/recall-graph/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/recall-graph) | Dormant | Advanced recall, graph traversal, embeddings, MMR packing, and memory cards. |

## Cross-Cutting Features Without Spec-X

These are deferred implementation surfaces that may later receive a `Spec-XN`
only if reintroduction work defines protocol behavior.

| Feature | Source | Status | Notes |
|---|---|---|---|
| Multi-tenant isolation | [`experimental/multi-tenant/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) | Dormant | Adds a tenant boundary above scopes; no `Spec-X` assigned yet. |
| Async jobs | [`experimental/async-jobs/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/async-jobs) | Dormant | Deferred async execution surface for long-running jobs. |
| Fuzzy resolver | [`experimental/fuzzy-resolver/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/fuzzy-resolver) | Dormant | Convenience resolver, not critical-path protocol behavior. |
| OIDC SSO | [`experimental/oidc-sso/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/oidc-sso) | Dormant | Adds an external identity-provider trust boundary. |
| Billing hooks | [`experimental/billing/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/billing) | Dormant | Commercial/operational concern; not part of the OSS default surface. |

## Storage And Embedding Surfaces

| Feature | Source | Status | Notes |
|---|---|---|---|
| Storage backend family | [`experimental/storage-backends/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/storage-backends) | Dormant | Backend abstractions beyond the v0.9.0a1 supported SQLite path. |
| libSQL/Turso storage | [`experimental/storage-libsql/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/storage-libsql) | Dormant | Adds third-party service trust and backend-specific behavior. |
| Cloud embedding providers | Recall graph / storage-backend material | Accepted risk | R-20 is accepted with operator warnings; local embeddings remain the supported default. |

## Adapters And SDKs

| Surface | Source | Status | Notes |
|---|---|---|---|
| MCP adapter package | [`experimental/mcp-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/mcp-adapter) | Deferred | Package metadata remains independent from v0.9.0a1. |
| Go SDK | [`experimental/sdk-go/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/sdk-go) | Dormant | Deferred until the Python SDK and protocol surface settle further. |
| Obsidian adapter | [`experimental/obsidian-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/obsidian-adapter) | Dormant | Requires adapter-specific threat modeling before promotion. |
| Cognee adapter | [`experimental/cognee-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/cognee-adapter) | Dormant | Preserved design-partner adapter. |
| Letta adapter | [`experimental/letta-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/letta-adapter) | Dormant | Preserved design-partner adapter. |
| Zep adapter | [`experimental/zep-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/zep-adapter) | Dormant | Preserved design-partner adapter. |
| Gemini adapter | [`experimental/gemini-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/gemini-adapter) | Dormant | Deferred model/tooling adapter. |
| Ollama/LiteLLM adapter | [`experimental/ollama-litellm-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/ollama-litellm-adapter) | Dormant | Deferred model/tooling adapter. |
| OpenAI tools adapter | [`experimental/openai-tools-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/openai-tools-adapter) | Dormant | Deferred model/tooling adapter. |
| Paperclip adapter | [`experimental/paperclip-adapter/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/paperclip-adapter) | Dormant | Deferred lifecycle/event adapter. |

## Deployment, UI, And Evaluation

| Surface | Source | Status | Notes |
|---|---|---|---|
| Curator dashboard | [`experimental/dashboard/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/dashboard) | Dormant | UI surface outside v0.9.0a1 default support. |
| Eval harness | [`experimental/eval-harness/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/eval-harness) | Dormant | Evaluation tooling, not a protocol feature. |
| Helm deployment | [`experimental/deploy-helm/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-helm) | Dormant | Docker Compose is the supported v0.9.0a1 deployment path. |
| Fly.io deployment | [`experimental/deploy-fly/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-fly) | Dormant | Deferred deployment recipe. |
| Grafana dashboards | [`experimental/deploy-grafana/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-grafana) | Dormant | Deferred observability recipe. |
| PaaS deployment | [`experimental/deploy-paas/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-paas) | Dormant | Deferred deployment recipe. |
| systemd deployment | [`experimental/deploy-systemd/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/deploy-systemd) | Dormant | Deferred deployment recipe. |

## Promotion Path

ADR-008 defines the five gates for any experimental feature:

1. Threat-model delta.
2. Accepted ADR or amendment.
3. Positive, negative, and adversarial conformance vectors wired into CI.
4. External operator soak with public bug reporting.
5. Documentation parity across Learn, Build, Operate, and Secure.

Gate progress lives in each feature's `STATUS.md`. Public pages summarize status;
they do not promote a feature by themselves.
