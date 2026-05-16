---
title: Alpha Tester Migration Guide
sidebar_label: Alpha Tester Migration
description: Migration guidance for testers moving from deferred or pre-plugin Stigmem feature flows to the v0.9.0aN plugin infrastructure path.
audience: Integrator
---

# Alpha Tester Migration Guide

**Audience:** Alpha testers who used deferred Stigmem feature surfaces before the plugin infrastructure landed.

The v0.9.0a1 default install is the supported critical-path surface. It includes typed facts, scopes, basic recall, federation, audit, SQLite storage, Docker Compose deployment, and CIDs as core behavior. It does not include production support for deferred feature behavior such as lazy instruction discovery, time-travel queries, RTBF tombstones, advanced Memory Garden ACLs, source attestation, multi-tenant isolation, or advanced recall graph features.

The plugin infrastructure now exists on `main`: stable 22-hook dispatch, package entry-point discovery, dependency ordering, lifecycle health checks, operator CLI inspection, production signing/trust policy, and author/operator documentation. Lazy instruction discovery and time-travel queries have been extracted as opt-in experimental plugin source packages under `experimental/`; signed/package artifact evidence is queued separately until all planned plugins are built. Other deferred feature plugins arrive later in the v0.9.0aN alpha series, one feature at a time.

Use this guide to decide what to keep testing now, what to disable, and what to wait for.

## What changed

| Area | v0.9.0a1 default behavior | Current `main` after plugin infrastructure | Later v0.9.0aN work |
|---|---|---|---|
| Default node install | No plugins required or registered. | Same default behavior; plugin support is opt-in. | Default install remains critical-path only. |
| Plugin package loading | Not in the first alpha artifact. | Entry-point discovery and startup registration are implemented; lazy-instruction and time-travel plugin source packages are extracted for validation. | Feature packages are published and installed explicitly as artifact refreshes land. |
| Plugin signing and trust | Not in the first alpha artifact. | Production registration requires verified signing/trust metadata; unsigned loading is development-only. | Package publication and feature-specific release hardening mature. |
| Deferred feature behavior | May exist in source, but is dormant or unsupported. | Still not promoted by plugin infrastructure alone; lazy instruction and time-travel behavior now require plugin registration/configuration. | Specific feature plugins ship behind explicit install/configuration. |
| Internal/pre-plugin test flows | Useful only as historical or local experiments. | Should be retired unless they test the supported default surface. | Replace with feature-plugin tests when each plugin lands. |

## Migration rules

1. **Do not rely on dormant code paths for production behavior.** If a feature is listed as experimental or dormant, treat it as unavailable in supported deployments.
2. **Do not assume a plugin exists because hooks exist.** Hook infrastructure is available now; feature plugins are separate packages that land later.
3. **Keep CIDs as core.** Content-addressed IDs are not moving to a plugin.
4. **Pin alpha artifacts.** Pre-1.0 builds do not carry a stability guarantee; pin exact versions and re-test on every upgrade.
5. **Use public docs and specs as the migration source.** The canonical public references are [Features](../../concepts/features.md), [Experimental Features](../../reference/experimental-features.md), the [Plugin Author Guide](./author-guide.md), and the [Operator Plugin Management Guide](../../operators/plugins/management.md).

## Feature destinations

| Feature or flow | Current status | Migration destination |
|---|---|---|
| Lazy instruction discovery | Experimental; opt-in plugin source extracted on `main`, with signed/package artifact evidence queued. ADR-008 graduation remains blocked on the capability redesign. | Default installs should keep using ordinary typed facts and explicit recall inputs. Test the plugin only in isolated alpha environments with explicit registration/configuration. |
| Content-addressed IDs | Core behavior. | Continue using the core CID/fact-ID behavior; do not plan for a CID plugin. |
| Time-travel `as_of` queries | Experimental; opt-in plugin source extracted on `main`, with signed/package artifact evidence deferred until all planned plugins are built. ADR-008 graduation remains open. | Default installs should expect `as_of` requests to fail closed with `time_travel_plugin_not_loaded`. Test the plugin only in isolated alpha environments with explicit registration. |
| RTBF tombstones | Experimental and dormant. | Wait for the tombstone plugin extraction and its operator/legal runbooks. Use ordinary retractions for current supported tests. |
| Memory Garden advanced ACL | Experimental and dormant. | Wait for the advanced ACL plugin extraction. Use stable scopes and basic garden behavior for current tests. |
| Source attestation | Experimental and dormant. | Wait for source-attestation plugin work and hardened identity/key lifecycle. Use existing API-key and audit attribution for current tests. |
| Multi-tenant isolation | Experimental implementation surface without a `Spec-X` assignment. | Wait for the multi-tenant plugin. Do not treat tenant isolation as part of the default install. |
| Subscriptions | Experimental and dormant. | Wait for a future subscription reintroduction path. Use polling or supported federation flows. |
| Intent envelope | Deferred indefinitely. | No migration target is available. Remove dependencies on this behavior. |
| Decay semantics | Experimental and dormant. | No current alpha feature-plugin commitment. Keep decay experiments isolated. |
| Synthesis | Experimental and dormant. | No current alpha feature-plugin commitment. Keep synthesis experiments isolated. |
| Recall graph, vector embeddings, MMR, memory cards | Experimental and dormant. | Wait for the recall-graph reintroduction path. The supported recall surface remains basic typed-fact retrieval. |
| Non-OpenClaw adapters | Experimental/dormant adapter surfaces. | Treat as unsupported until each adapter passes the reintroduction gates. |
| Helm, Fly.io, systemd, Grafana, PaaS deployment recipes | Experimental deployment surfaces. | Use Docker Compose for supported v0.9.0a1 testing; keep other deployment recipes isolated. |

## What to test now

Use current `main` or the next alpha artifact to test the plugin infrastructure itself:

- Author a minimal plugin using the [Plugin Author Guide](./author-guide.md).
- Register only hooks from the [Plugin Hook Reference](../../reference/plugin-api/hooks.md).
- Declare capabilities from the [Plugin Capability Reference](../../reference/plugin-api/capabilities.md).
- Install and inspect plugins using the [Operator Plugin Management Guide](../../operators/plugins/management.md).
- Verify default behavior with no plugins registered.
- Verify production signing/trust policy and development-only unsigned loading.

Do not test a deferred feature as though it has graduated just because its future hook points now exist.

## Retiring pre-plugin tests

If you have tests written before the plugin infrastructure landed, sort them into three groups:

| Test type | Action |
|---|---|
| Default-surface tests | Keep them, but remove assumptions about deferred feature behavior. |
| Plugin-infrastructure tests | Rewrite them around manifest, hook, capability, signing, CLI, health, and audit behavior. |
| Deferred-feature behavior tests | Move them to the relevant feature's experimental area or mark them blocked until that feature plugin exists. |

For plugin-infrastructure tests, prefer small fixtures that exercise `PluginManifest`, `PluginContext`, the registry firing method for the hook semantic, and expected fail-closed behavior.

## Operator checklist

Before enabling tester plugins in a shared environment:

- Pin the plugin package version.
- Keep `STIGMEM_PLUGIN_SIGNING_REQUIRED=true`.
- Set `STIGMEM_PLUGIN_TRUSTED_PUBLISHERS` to reviewed signing identities.
- Use `STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS` only for explicit, short-lived exceptions.
- Run `stigmem plugins list --json` and `stigmem plugins describe <name> --json` after startup.
- Review `plugin.registered`, `plugin.registration_failed`, `plugin.handler_denied`, and `plugin.handler_error` audit events.

## References

- [Features](../../concepts/features.md)
- [Experimental Features](../../reference/experimental-features.md)
- [Roadmap](https://github.com/Eidetic-Labs/stigmem/blob/main/ROADMAP.md)
- [Plugin Author Guide](./author-guide.md)
- [Plugin Hook Reference](../../reference/plugin-api/hooks.md)
- [Plugin Capability Reference](../../reference/plugin-api/capabilities.md)
- [Operator Plugin Management Guide](../../operators/plugins/management.md)
