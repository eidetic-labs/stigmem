# Feature Tracker

This tracker mirrors the public [feature matrix](../docs/concepts/features.md)
and [experimental features index](../docs/reference/experimental-features.md)
without making public docs depend on internal planning files.

## Current Public Surfaces

| Surface | Purpose |
|---|---|
| [`docs/docs/concepts/features.md`](../docs/concepts/features.md) | Public v0.9.0a1 feature matrix and supported/default-surface summary. |
| [`docs/docs/reference/experimental-features.md`](../docs/reference/experimental-features.md) | Public index of deferred and experimental surfaces. |
| [`experimental/README.md`](../../experimental/README.md) | Repo-level implementation index for experimental directories. |

## Protocol-Bearing Experimental Features

| Feature | Spec | Source | Status source |
|---|---|---|---|
| Lazy instruction discovery | `Spec-X1-Lazy-Instruction-Discovery` | `experimental/lazy-instruction-discovery/spec.md` | [`STATUS.md`](../../experimental/lazy-instruction-discovery/STATUS.md) |
| RTBF tombstones | `Spec-X2-RTBF-Tombstones` | `experimental/tombstones/spec.md` | [`STATUS.md`](../../experimental/tombstones/STATUS.md) |
| Time-travel queries | `Spec-X3-Time-Travel-Queries` | `experimental/time-travel/spec.md` | [`STATUS.md`](../../experimental/time-travel/STATUS.md) |
| Memory Garden advanced ACL | `Spec-X5-Memory-Garden-Advanced-ACL` | `experimental/memory-garden-acl/spec.md` | [`STATUS.md`](../../experimental/memory-garden-acl/STATUS.md) |
| Source attestation | `Spec-X6-Source-Attestation` | `experimental/source-attestation/spec.md` | [`STATUS.md`](../../experimental/source-attestation/STATUS.md) |
| Subscriptions | `Spec-X7-Subscriptions` | `experimental/subscriptions/spec.md` | [`STATUS.md`](../../experimental/subscriptions/STATUS.md) |
| Intent envelope | `Spec-X8-Intent-Envelope` | `experimental/intent-envelope/spec.md` | [`STATUS.md`](../../experimental/intent-envelope/STATUS.md) |
| Decay semantics | `Spec-X9-Decay-Semantics` | `experimental/decay/spec.md` | [`STATUS.md`](../../experimental/decay/STATUS.md) |
| Synthesis | `Spec-X10-Synthesis` | `experimental/synthesis/spec.md` | [`STATUS.md`](../../experimental/synthesis/STATUS.md) |
| Recall graph | `Spec-X11-Recall-Graph` | `experimental/recall-graph/spec.md` | [`STATUS.md`](../../experimental/recall-graph/STATUS.md) |

## Experimental Surfaces Without Spec-X

These surfaces remain tracked by `STATUS.md`. Assign a `Spec-XN-*` only if
future reintroduction work defines protocol behavior.

| Group | Directories |
|---|---|
| Cross-cutting features | `experimental/multi-tenant/`, `experimental/async-jobs/`, `experimental/fuzzy-resolver/`, `experimental/oidc-sso/`, `experimental/billing/` |
| Storage and embedding | `experimental/storage-backends/`, `experimental/storage-libsql/` |
| Adapters and SDKs | `experimental/mcp-adapter/`, `experimental/sdk-go/`, `experimental/obsidian-adapter/`, `experimental/cognee-adapter/`, `experimental/letta-adapter/`, `experimental/zep-adapter/`, `experimental/gemini-adapter/`, `experimental/ollama-litellm-adapter/`, `experimental/openai-tools-adapter/`, `experimental/paperclip-adapter/` |
| Deployment, UI, and evaluation | `experimental/dashboard/`, `experimental/eval-harness/`, `experimental/deploy-helm/`, `experimental/deploy-fly/`, `experimental/deploy-grafana/`, `experimental/deploy-paas/`, `experimental/deploy-systemd/` |

## Maintenance Rules

- Keep the public feature matrix concise; it names status and points to the full
  experimental index.
- Keep the public experimental index complete and operator-readable.
- Keep per-feature gate details in each `experimental/<feature>/STATUS.md`.
- Do not add a public docs link to this internal tracker; internal docs may link
  outward to public pages.

## 2026-05-16 PR 4c Closeout

- Time-travel query source now lives under
  `experimental/time-travel/` as `stigmem-plugin-time-travel`.
- Default installs reject `as_of` requests with
  `time_travel_plugin_not_loaded`; plugin-loaded validation covers fact query,
  recall, deterministic hook ordering, and plugin-required conformance vectors.
- Signed/package artifact evidence remains deferred until the planned plugin set
  is built.
