---
title: Plugin Author Guide
sidebar_label: Author Guide
description: Build a minimal Stigmem plugin with the v0.9.0a1 manifest, hook, capability, signing, and test APIs.
audience: Integrator
---

# Plugin Author Guide

**Audience:** Developers writing opt-in Stigmem plugins for the v0.9.0aN alpha series.

Plugins extend a node through the stable 22-hook surface introduced for the v0.9.0a1 architecture-in-flight line. A plugin package contributes a `PluginManifest`, declares the capabilities it needs, registers hook handlers, and is loaded at node startup through the `stigmem.plugins` Python entry point group.

The default install still runs without plugins. Production nodes should only load plugins that have passed the signing and trusted-publisher checks described below.

## Minimal package layout

Create a normal Python package that can be installed into the same environment as `stigmem-node`:

```text
example-stigmem-plugin/
  pyproject.toml
  src/
    example_stigmem_plugin/
      __init__.py
  tests/
    test_plugin.py
```

`pyproject.toml` declares the plugin entry point:

```toml
[project]
name = "example-stigmem-plugin"
version = "1.0.0"
requires-python = ">=3.12"
dependencies = [
  "stigmem-node>=0.9.0a1",
]

[project.entry-points."stigmem.plugins"]
example_stigmem_plugin = "example_stigmem_plugin:plugin_manifest"
```

The entry point value must resolve to a zero-argument callable that returns a `PluginManifest`.

## Manifest and hook handlers

This example denies writes from a blocked source and records a no-op audit hook so the plugin exercises both voting and fire-and-forget hook patterns:

```python
from __future__ import annotations

from stigmem_node.plugins import Allow, Deny, PluginContext, PluginManifest

BLOCKED_SOURCE = "agent:blocked"


def pre_assert_authorize(
    _ctx: PluginContext,
    *,
    source: str | None = None,
    **_: object,
) -> Allow | Deny:
    if source == BLOCKED_SOURCE:
        return Deny("source is blocked by example-stigmem-plugin")
    return Allow()


def post_assert_audit(_ctx: PluginContext, **_: object) -> None:
    return None


def plugin_manifest() -> PluginManifest:
    return PluginManifest(
        name="example-stigmem-plugin",
        version="1.0.0",
        requires_stigmem=">=0.9.0a1",
        capabilities=frozenset(),
        hooks={
            "pre_assert_authorize": pre_assert_authorize,
            "post_assert_audit": post_assert_audit,
        },
    )
```

Manifest fields:

| Field | Required | Purpose |
|---|---:|---|
| `name` | Yes | Stable plugin name. Use lowercase letters, numbers, and hyphens. |
| `version` | Yes | Plugin package version. |
| `requires_stigmem` | No | Compatibility line. Use `>=0.9.0a1` unless your plugin requires a later alpha. |
| `capabilities` | No | Capability names the plugin may access through `PluginContext`. |
| `hooks` | No | Mapping from stable hook name to callable handler. |
| `health_check` | No | Lifecycle health callable used by operator inspection. |
| `depends_on` | No | Other plugin names that must register before this plugin. |

## Hook patterns

Handlers always receive a `PluginContext` as the first positional argument. Hook-specific payloads are supplied as keyword arguments, except filter-chain hooks receive the current value as the second positional argument.

Use these return shapes:

| Hook semantic | Handler pattern | Return value |
|---|---|---|
| Voting | authorize or validate a request | `Allow()` or `Deny("reason")` |
| Filter chain | rewrite a payload | the transformed value, never `None` |
| Score delta | adjust recall ranking | `dict[str, float]` keyed by result or fact id |
| Fire and forget | audit or observe side effects | `None` |

The stable v0.9.0a1 hook names are defined in the [hook source reference](https://github.com/Eidetic-Labs/stigmem/blob/main/node/src/stigmem_node/plugins/hooks.py). Do not register hooks outside that list; `health_check` is a manifest lifecycle callable, not a hook name.

## Capability declarations

`PluginContext` is capability gated. Declaring a capability in the manifest is required before a handler can ask the context for the corresponding core API handle.

```python
from stigmem_node.plugins import PluginContext, PluginManifest


def post_assert_audit(ctx: PluginContext, **_: object) -> None:
    audit = ctx.get_audit_emitter()
    if callable(audit):
        audit({"event_type": "example.plugin.post_assert"})


def plugin_manifest() -> PluginManifest:
    return PluginManifest(
        name="example-audit-plugin",
        version="1.0.0",
        requires_stigmem=">=0.9.0a1",
        capabilities=frozenset({"audit.emit"}),
        hooks={"post_assert_audit": post_assert_audit},
    )
```

The v0.9.0a1 `CoreApis` handles are deliberately narrow and optional. Operators or tests may expose a callable or facade object behind a capability; plugins should handle `None` or an unexpected shape explicitly. If a handler calls `ctx.get_audit_emitter()` without declaring `audit.emit`, registration can succeed but the handler will fail with a capability error when the hook fires.

The v0.9.0a1 capability allowlist is defined in the [capability source reference](https://github.com/Eidetic-Labs/stigmem/blob/main/node/src/stigmem_node/plugins/capabilities.py).

## Local tests

Unit-test plugins without booting a node by registering the manifest in a `HookRegistry`:

```python
from stigmem_node.plugins import Deny, HookRegistry

from example_stigmem_plugin import plugin_manifest


def test_blocks_configured_source() -> None:
    registry = HookRegistry()
    registry.register_plugin(plugin_manifest())

    decision = registry.fire_voting(
        "pre_assert_authorize",
        source="agent:blocked",
    )

    assert isinstance(decision, Deny)
    assert decision.reason == "source is blocked by example-stigmem-plugin"
```

For tests that need to replace the process-global registry temporarily, use the [testing helper reference](https://github.com/Eidetic-Labs/stigmem/blob/main/node/src/stigmem_node/plugins/testing.py):

```python
from stigmem_node.plugins.testing import stigmem_plugins

from example_stigmem_plugin import plugin_manifest


def test_process_registry_fixture() -> None:
    with stigmem_plugins([plugin_manifest()]) as registry:
        assert "example-stigmem-plugin" in registry.registered_plugins()
```

Run the plugin test suite in an environment that has both your package and `stigmem-node>=0.9.0a1` installed.

## Startup loading

After installing the plugin package, Stigmem discovers entry points from the `stigmem.plugins` group and registers them during startup. Dependency ordering is deterministic: dependencies listed in `depends_on` register before the dependent plugin, and cycles fail closed.

For local development only, an operator may load unsigned plugins by setting:

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=false
```

That setting emits a security warning and audit metadata. Do not use it in production.

## Signing and trust expectations

Production plugin registration requires a verified signing identity. The current registration boundary expects discovered plugins to arrive with verified signing metadata and then applies operator trust policy:

- `STIGMEM_PLUGIN_TRUSTED_PUBLISHERS` lists accepted signing identities.
- `STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS` lists explicit audited exceptions.
- Unsigned plugins are rejected when `STIGMEM_PLUGIN_SIGNING_REQUIRED=true`.

The signing gate is implemented in the [signing source reference](https://github.com/Eidetic-Labs/stigmem/blob/main/node/src/stigmem_node/plugins/signing.py). Operator-facing trust setup is covered separately in the plugin management guide.

## Author checklist

Before publishing a plugin:

- Use `requires_stigmem=">=0.9.0a1"` or a later alpha bound that matches your tested API surface.
- Register only stable hook names from the 22-hook surface.
- Declare only capabilities your handlers actually use.
- Add unit tests for allow, deny, and error paths.
- Verify startup discovery through the `stigmem.plugins` entry point.
- Coordinate signing identity and trusted-publisher configuration with the node operator.
