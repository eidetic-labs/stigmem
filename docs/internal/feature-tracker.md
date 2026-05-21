# Feature Record Migration Inventory

This inventory tracks the ADR-020 migration from legacy feature documentation
to canonical feature records under `features/<feature-slug>/`.

It is an operational migration control document, not a second feature dossier.
Rows identify where feature truth lives today, where the feature record will
live, and which release horizon should drive migration order. Once a feature is
marked `migrated`, the feature record owns feature detail and legacy paths must
act only as wrappers, compatibility projections, or implementation directories.

## Public Surfaces

| Surface | Purpose |
| --- | --- |
| [`docs/docs/concepts/features.md`](../docs/concepts/features.md) | Public feature matrix and supported/default-surface summary. |
| [`docs/docs/reference/experimental-features.md`](../docs/reference/experimental-features.md) | Public index of deferred and experimental surfaces. |
| [`experimental/README.md`](../../experimental/README.md) | Repo-level implementation index for experimental directories. |
| [`features/README.md`](../../features/README.md) | Feature record contract and metadata rules. |

## Migration Status Values

| Status | Meaning |
| --- | --- |
| `migrated` | Complete six-file feature record exists and owns feature detail. |
| `pending` | Legacy docs remain the owner until a feature record PR migrates the row. |
| `deferred` | Feature record is not planned for the active alpha horizon. |
| `superseded` | Legacy feature family is intentionally retired or replaced. |

## Feature Record Migration Inventory

| Feature ID | Feature | Type | Stability | Default surface | Canonical spec | Legacy owner | Target record | Migration status | Horizon | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `content-addressed-ids` | Content-addressed fact IDs | `core` | `stable` | `default` | `Spec-21-Content-Addressed-IDs` | `spec/specs/21-content-addressed-ids.md` | `features/content-addressed-ids/` | `migrated` | `v0.9.0a3` | Pilot core feature record. Legacy spec path is a compatibility projection. |
| `time-travel` | Time-travel queries | `plugin` | `experimental` | `opt-in` | `Spec-X3-Time-Travel-Queries` | `experimental/time-travel/` | `features/time-travel/` | `migrated` | `v0.9.0a4` | Pilot plugin-backed feature record. Implementation remains under `experimental/time-travel/`. |
| `lazy-instruction-discovery` | Lazy instruction discovery | `plugin` | `experimental` | `opt-in` | `Spec-X1-Lazy-Instruction-Discovery` | `experimental/lazy-instruction-discovery/` | `features/lazy-instruction-discovery/` | `pending` | `0.9.xA` | Protocol-bearing experimental plugin candidate. |
| `tombstones` | RTBF tombstones | `plugin` | `experimental` | `opt-in` | `Spec-X2-RTBF-Tombstones` | `experimental/tombstones/` | `features/tombstones/` | `pending` | `0.9.xA` | Security-sensitive migration should preserve R-16/R-17 ownership. |
| `memory-garden-acl` | Memory Garden advanced ACL | `plugin` | `experimental` | `opt-in` | `Spec-X5-Memory-Garden-Advanced-ACL` | `experimental/memory-garden-acl/` | `features/memory-garden-acl/` | `pending` | `0.9.xA` | Protocol-bearing experimental plugin candidate. |
| `source-attestation` | Source attestation | `plugin` | `experimental` | `opt-in` | `Spec-X6-Source-Attestation` | `experimental/source-attestation/` | `features/source-attestation/` | `pending` | `0.9.xA` | Security and release-supply-chain references must be preserved. |
| `subscriptions` | Subscriptions | `protocol` | `experimental` | `opt-in` | `Spec-X7-Subscriptions` | `experimental/subscriptions/` | `features/subscriptions/` | `pending` | `0.9.xA` | Protocol-bearing experimental feature. |
| `intent-envelope` | Intent envelope | `protocol` | `experimental` | `opt-in` | `Spec-X8-Intent-Envelope` | `experimental/intent-envelope/` | `features/intent-envelope/` | `pending` | `0.9.xA` | Protocol-bearing experimental feature. |
| `decay` | Decay semantics | `protocol` | `experimental` | `opt-in` | `Spec-X9-Decay-Semantics` | `experimental/decay/` | `features/decay/` | `pending` | `0.9.xA` | Protocol-bearing experimental feature. |
| `synthesis` | Synthesis | `protocol` | `experimental` | `opt-in` | `Spec-X10-Synthesis` | `experimental/synthesis/` | `features/synthesis/` | `pending` | `0.9.xA` | Protocol-bearing experimental feature. |
| `recall-graph` | Recall graph | `protocol` | `experimental` | `opt-in` | `Spec-X11-Recall-Graph` | `experimental/recall-graph/` | `features/recall-graph/` | `pending` | `0.9.xA` | Protocol-bearing experimental feature. |
| `multi-tenant` | Multi-tenant scoping | `plugin` | `experimental` | `opt-in` | `none` | `experimental/multi-tenant/` | `features/multi-tenant/` | `pending` | `0.9.xA` | Security-contributing cross-cutting feature; assign spec only if protocol work reopens. |
| `async-jobs` | Async jobs | `core` | `experimental` | `opt-in` | `none` | `experimental/async-jobs/` | `features/async-jobs/` | `pending` | `future alpha` | No Spec-X assigned. |
| `fuzzy-resolver` | Fuzzy resolver | `core` | `experimental` | `opt-in` | `none` | `experimental/fuzzy-resolver/` | `features/fuzzy-resolver/` | `pending` | `future alpha` | No Spec-X assigned. |
| `oidc-sso` | OIDC SSO | `core` | `experimental` | `opt-in` | `none` | `experimental/oidc-sso/` | `features/oidc-sso/` | `pending` | `future alpha` | No Spec-X assigned. |
| `billing` | Billing | `core` | `experimental` | `opt-in` | `none` | `experimental/billing/` | `features/billing/` | `deferred` | `future gate` | Business feature outside active alpha release scope. |
| `storage-backends` | Storage backends | `adapter` | `experimental` | `opt-in` | `none` | `experimental/storage-backends/` | `features/storage-backends/` | `pending` | `future alpha` | Storage-family parent row. |
| `storage-libsql` | libSQL storage | `adapter` | `experimental` | `opt-in` | `none` | `experimental/storage-libsql/` | `features/storage-libsql/` | `pending` | `future alpha` | Adapter-specific storage feature. |
| `mcp-adapter` | MCP adapter | `adapter` | `experimental` | `external` | `none` | `experimental/mcp-adapter/` | `features/mcp-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `sdk-go` | Go SDK | `sdk` | `experimental` | `external` | `none` | `experimental/sdk-go/` | `features/sdk-go/` | `pending` | `future alpha` | SDK surface. |
| `obsidian-adapter` | Obsidian adapter | `adapter` | `experimental` | `external` | `none` | `experimental/obsidian-adapter/` | `features/obsidian-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `cognee-adapter` | Cognee adapter | `adapter` | `experimental` | `external` | `none` | `experimental/cognee-adapter/` | `features/cognee-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `letta-adapter` | Letta adapter | `adapter` | `experimental` | `external` | `none` | `experimental/letta-adapter/` | `features/letta-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `zep-adapter` | Zep adapter | `adapter` | `experimental` | `external` | `none` | `experimental/zep-adapter/` | `features/zep-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `gemini-adapter` | Gemini adapter | `adapter` | `experimental` | `external` | `none` | `experimental/gemini-adapter/` | `features/gemini-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `ollama-litellm-adapter` | Ollama/LiteLLM adapter | `adapter` | `experimental` | `external` | `none` | `experimental/ollama-litellm-adapter/` | `features/ollama-litellm-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `openai-tools-adapter` | OpenAI tools adapter | `adapter` | `experimental` | `external` | `none` | `experimental/openai-tools-adapter/` | `features/openai-tools-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `paperclip-adapter` | Paperclip adapter | `adapter` | `experimental` | `external` | `none` | `experimental/paperclip-adapter/` | `features/paperclip-adapter/` | `pending` | `future alpha` | Adapter surface. |
| `dashboard` | Dashboard | `tooling` | `experimental` | `internal` | `none` | `experimental/dashboard/` | `features/dashboard/` | `pending` | `future alpha` | UI/tooling surface. |
| `eval-harness` | Evaluation harness | `tooling` | `experimental` | `internal` | `none` | `experimental/eval-harness/` | `features/eval-harness/` | `pending` | `future alpha` | Evaluation tooling. |
| `deploy-helm` | Helm deployment | `deployment` | `experimental` | `external` | `none` | `experimental/deploy-helm/` | `features/deploy-helm/` | `pending` | `future alpha` | Deployment surface. |
| `deploy-fly` | Fly.io deployment | `deployment` | `experimental` | `external` | `none` | `experimental/deploy-fly/` | `features/deploy-fly/` | `pending` | `future alpha` | Deployment surface. |
| `deploy-grafana` | Grafana deployment | `deployment` | `experimental` | `external` | `none` | `experimental/deploy-grafana/` | `features/deploy-grafana/` | `pending` | `future alpha` | Deployment/observability surface. |
| `deploy-paas` | PaaS deployment | `deployment` | `experimental` | `external` | `none` | `experimental/deploy-paas/` | `features/deploy-paas/` | `pending` | `future alpha` | Deployment surface. |
| `deploy-systemd` | systemd deployment | `deployment` | `experimental` | `external` | `none` | `experimental/deploy-systemd/` | `features/deploy-systemd/` | `pending` | `future alpha` | Deployment surface. |

## Maintenance Rules

- Do not add feature behavior, security analysis, or release-note detail to this
  inventory. Put that material in the feature record once migrated.
- Keep `Migration status` accurate when a feature record PR lands.
- `migrated` rows must point to a real `features/<feature-slug>/` directory and
  pass `scripts/check_feature_records.py`.
- `pending` rows identify the current legacy owner until migration.
- `deferred` rows remain visible so future-horizon work is not lost.
- Public docs may summarize feature status, but this inventory remains internal.
