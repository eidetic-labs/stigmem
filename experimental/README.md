# Experimental Features

Implementation-facing index for features outside the v0.9.0a1 default surface.
The public operator-facing index is
[`docs/docs/reference/experimental-features.md`](../docs/docs/reference/experimental-features.md).

Experimental does not mean "almost stable." These features are opt-in,
unsupported for production reliance, and must pass the five gates in
[ADR-008](../docs/adr/008-experimental-gates.md) before they can graduate into
the supported surface. The v0.9.0a1 scope boundary is defined by
[ADR-002](../docs/adr/002-v1-scope.md).

## Conventions

- Every experimental directory carries `STATUS.md`.
- Protocol-bearing deferred features have exactly one colocated
  `experimental/<feature>/spec.md` and one rendered `Spec-XN-*` page.
- Adapters, SDKs, dashboards, deployment recipes, and tooling stay
  `STATUS.md`-tracked unless they later define protocol behavior.
- Gate progress is appended to the feature's `STATUS.md`; the public docs only
  summarize current status and source location.

## Protocol Features

| Feature | Spec | Status |
|---|---|---|
| Lazy instruction discovery | [`Spec-X1-Lazy-Instruction-Discovery`](lazy-instruction-discovery/spec.md) | [STATUS](lazy-instruction-discovery/STATUS.md) |
| RTBF tombstones | [`Spec-X2-RTBF-Tombstones`](tombstones/spec.md) | [STATUS](tombstones/STATUS.md) |
| Time-travel queries | [`Spec-X3-Time-Travel-Queries`](time-travel/spec.md) | [STATUS](time-travel/STATUS.md) |
| Memory Garden advanced ACL | [`Spec-X5-Memory-Garden-Advanced-ACL`](../features/memory-garden-acl/spec.md) | [STATUS](../features/memory-garden-acl/status.md) |
| Source attestation | [`Spec-X6-Source-Attestation`](source-attestation/spec.md) | [STATUS](source-attestation/STATUS.md) |
| Subscriptions | [`Spec-X7-Subscriptions`](../features/subscriptions/spec.md) | [STATUS](../features/subscriptions/status.md) |
| Intent envelope | [`Spec-X8-Intent-Envelope`](../features/intent-envelope/spec.md) | [STATUS](../features/intent-envelope/status.md) |
| Decay semantics | [`Spec-X9-Decay-Semantics`](../features/decay/spec.md) | [STATUS](../features/decay/status.md) |
| Synthesis | [`Spec-X10-Synthesis`](../features/synthesis/spec.md) | [STATUS](../features/synthesis/status.md) |
| Recall graph | [`Spec-X11-Recall-Graph`](../features/recall-graph/spec.md) | [STATUS](../features/recall-graph/status.md) |

## Cross-Cutting Features Without Spec-X

| Feature | Status |
|---|---|
| Multi-tenant isolation | [STATUS](multi-tenant/STATUS.md) |
| Async jobs | [STATUS](async-jobs/STATUS.md) |
| Fuzzy resolver | [STATUS](fuzzy-resolver/STATUS.md) |
| OIDC SSO | [STATUS](oidc-sso/STATUS.md) |
| Billing hooks | [STATUS](billing/STATUS.md) |

## Storage And Embedding Surfaces

| Surface | Status |
|---|---|
| Storage backend family | [STATUS](storage-backends/STATUS.md) |
| libSQL/Turso storage | [STATUS](storage-libsql/STATUS.md) |
| Cloud embedding providers | Tracked through recall graph/storage-backend work and accepted-risk documentation. |

## Adapters And SDKs

| Surface | Status |
|---|---|
| MCP adapter package | [STATUS](mcp-adapter/STATUS.md) |
| Go SDK | [STATUS](sdk-go/STATUS.md) |
| Obsidian adapter | [STATUS](obsidian-adapter/STATUS.md) |
| Cognee adapter | [STATUS](cognee-adapter/STATUS.md) |
| Letta adapter | [STATUS](letta-adapter/STATUS.md) |
| Zep adapter | [STATUS](zep-adapter/STATUS.md) |
| Gemini adapter | [STATUS](gemini-adapter/STATUS.md) |
| Ollama/LiteLLM adapter | [STATUS](ollama-litellm-adapter/STATUS.md) |
| OpenAI tools adapter | [STATUS](openai-tools-adapter/STATUS.md) |
| Paperclip adapter | [STATUS](paperclip-adapter/STATUS.md) |

## Deployment, UI, And Evaluation

| Surface | Status |
|---|---|
| Curator dashboard | [STATUS](dashboard/STATUS.md) |
| Eval harness | [STATUS](eval-harness/STATUS.md) |
| Helm deployment | [STATUS](deploy-helm/STATUS.md) |
| Fly.io deployment | [STATUS](deploy-fly/STATUS.md) |
| Grafana dashboards | [STATUS](deploy-grafana/STATUS.md) |
| PaaS deployment | [STATUS](deploy-paas/STATUS.md) |
| systemd deployment | [STATUS](deploy-systemd/STATUS.md) |

## Adding A New Experimental Feature

1. Create `experimental/<feature>/`.
2. Add `experimental/<feature>/STATUS.md`.
3. Add `experimental/<feature>/spec.md` only when the feature defines protocol
   behavior.
4. Add the feature to this index and to the public experimental-features page.
5. Open or update the tracking issue tagged for that experimental feature.

The feature remains experimental until it passes ADR-008. It may be excluded
from default builds, default test runs, and default documentation.
