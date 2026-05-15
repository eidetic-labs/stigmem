---
title: Plugin Hook Reference
sidebar_label: Hooks
description: Stable v0.9.0a1 plugin hook names, semantics, ordering policies, and handler shapes.
audience: Integrator
---

# Plugin Hook Reference

**Audience:** Plugin authors and integrators who need the stable v0.9.0a1 hook surface.

This page documents the 22-hook surface defined for PR 4-INF.1 and used by the v0.9.0aN plugin infrastructure. It is aligned with `node/src/stigmem_node/plugins/hooks.py`. Do not add hook names beyond this list for v0.9.0a1-compatible plugins.

For a complete package example, start with the [Plugin Author Guide](../../guides/plugins/author-guide.md).

## Handler semantics

Every handler receives a `PluginContext` as its first positional argument. Hook-site payloads are passed as keyword arguments unless the semantic says a current value is passed positionally.

| Semantic | Registry method | Handler shape | Expected return |
|---|---|---|---|
| `voting` | `fire_voting(hook, **kwargs)` | `def handler(ctx: PluginContext, **kwargs: object) -> Allow | Deny` | `Allow()` or `Deny("reason")` |
| `filter_chain` | `fire_filter_chain(hook, value, **kwargs)` | `def handler(ctx: PluginContext, value: T, **kwargs: object) -> T` | The transformed value. Returning `None` is an error. |
| `score_delta` | `fire_score_delta(hook, scored_results, **kwargs)` | `def handler(ctx: PluginContext, scored_results: list[object], **kwargs: object) -> dict[str, float]` | Score deltas keyed by result or fact id. Deltas are summed across handlers. |
| `fire_and_forget` | `fire_fire_and_forget(hook, **kwargs)` | `def handler(ctx: PluginContext, **kwargs: object) -> None` | `None`. Audit hooks marked strict raise on handler failure. |

## Ordering policies

| Policy | Meaning |
|---|---|
| `core_first` | Core handlers run first, then plugin handlers in deterministic plugin order. |
| `plugins_first` | Plugin handlers run before any core handlers. |
| `core_only_default` | Core behavior is the default path; plugins may observe or extend where registered. |
| `plugin_only` | Only plugin handlers run for the hook. |

## Stable hook surface

| Hook | Semantic | Ordering | Handler shape | Notes |
|---|---|---|---|---|
| `pre_assert_authorize` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Authorize a fact assertion before validation and persistence. |
| `pre_assert_validate` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Validate an assertion payload before transformation. |
| `pre_assert_transform` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Rewrite or normalize the assertion payload. |
| `post_assert_persist` | `fire_and_forget` | `plugin_only` | `def handler(ctx, **kwargs) -> None` | Observe post-persistence assertion effects. |
| `post_assert_propagate` | `fire_and_forget` | `plugin_only` | `def handler(ctx, **kwargs) -> None` | Observe propagation scheduling after assertion. |
| `post_assert_audit` | `fire_and_forget` | `core_only_default` | `def handler(ctx, **kwargs) -> None` | Strict audit hook. Handler failure is surfaced. |
| `pre_recall_authorize` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Authorize a recall request. |
| `pre_recall_rewrite` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Rewrite the recall query or request payload. |
| `recall_filter` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Filter recall candidates or result collections. |
| `recall_rank` | `score_delta` | `plugins_first` | `def handler(ctx, scored_results, **kwargs) -> dict[str, float]` | Add rank score deltas by result or fact id. |
| `post_recall_audit` | `fire_and_forget` | `core_only_default` | `def handler(ctx, **kwargs) -> None` | Strict audit hook for recall completion. |
| `federation_peer_authenticate` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Authenticate a federation peer. |
| `federation_inbound_validate` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Validate inbound federation data. |
| `federation_inbound_filter` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Filter or rewrite inbound federation facts. |
| `federation_outbound_filter` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Filter outbound federation payloads. |
| `federation_outbound_sign` | `filter_chain` | `plugins_first` | `def handler(ctx, value, **kwargs) -> object` | Add or transform outbound signing material. |
| `identity_resolve` | `filter_chain` | `core_first` | `def handler(ctx, value, **kwargs) -> object` | Resolve identity context from authentication material. |
| `tenant_resolve` | `filter_chain` | `core_first` | `def handler(ctx, value, **kwargs) -> object` | Resolve tenant context for a request. |
| `capability_check` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Authorize capability use. |
| `migration_register` | `filter_chain` | `core_only_default` | `def handler(ctx, value, **kwargs) -> list[Migration]` | Register plugin-owned migrations; plugin migrations must remain namespaced to their declaring plugin. |
| `audit_emit` | `fire_and_forget` | `core_only_default` | `def handler(ctx, **kwargs) -> None` | Strict audit hook for normalized audit events. Handler failure is surfaced. |
| `config_validate` | `voting` | `core_first` | `def handler(ctx, **kwargs) -> Allow | Deny` | Validate plugin or node configuration before registration proceeds. |

## Lifecycle health is not a hook

`health_check` is a `PluginManifest` lifecycle callable used by operator inspection and health reporting. It is not part of the 22-hook PR 4-INF.1 surface and must not appear in the manifest `hooks` mapping. Health-check behavior belongs to the plugin lifecycle/operator documentation, not to hook dispatch.
