---
title: Plugin Author Guide
sidebar_label: Author Guide
description: Build a minimal Stigmem plugin with the v0.9.0a1 manifest, hook, capability, signing, and test APIs.
audience: Integrator
---

# Plugin Author Guide

<p className="stigmem-meta"><span>5 min read</span><span>Plugin author</span><span>v0.9.0aN alpha</span></p>

<div className="stigmem-lead">

**What this guide covers**

Build a minimal Stigmem plugin against the stable 22-hook surface
introduced for the v0.9.0a1 architecture-in-flight line. A plugin
package contributes a `PluginManifest`, declares the capabilities
it needs, registers hook handlers, and is loaded at node startup
through the `stigmem.plugins` Python entry point group.

</div>

**Audience:** Developers writing opt-in Stigmem plugins for the v0.9.0aN alpha series.

<div className="stigmem-keypoint">

**The default install still runs without plugins.**

Production nodes should only load plugins that have passed the
signing and trusted-publisher checks described below.

</div>

## Minimal package layout

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

**Manifest fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>name</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Stable plugin name. Use lowercase letters, numbers, and hyphens.</dd>
</div>

<div>
<dt><code>version</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Plugin package version.</dd>
</div>

<div>
<dt><code>requires_stigmem</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Compatibility line. Use <code>&gt;=0.9.0a1</code> unless your plugin requires a later alpha.</dd>
</div>

<div>
<dt><code>capabilities</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Capability names the plugin may access through <code>PluginContext</code>.</dd>
</div>

<div>
<dt><code>hooks</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Mapping from stable hook name to callable handler.</dd>
</div>

<div>
<dt><code>health_check</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Lifecycle health callable used by operator inspection.</dd>
</div>

<div>
<dt><code>depends_on</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Other plugin names that must register before this plugin.</dd>
</div>

</div>

## Hook patterns

Handlers always receive a `PluginContext` as the first positional argument. Hook-specific payloads are supplied as keyword arguments, except filter-chain hooks receive the current value as the second positional argument.

<div className="stigmem-fields">

<div>
<dt>Semantic</dt>
<dt><span className="stigmem-fields__type">Handler pattern</span></dt>
<dd>Return value</dd>
</div>

<div>
<dt>Voting</dt>
<dt><span className="stigmem-fields__type">authorize / validate</span></dt>
<dd><code>Allow()</code> or <code>Deny("reason")</code>.</dd>
</div>

<div>
<dt>Filter chain</dt>
<dt><span className="stigmem-fields__type">rewrite payload</span></dt>
<dd>The transformed value, never <code>None</code>.</dd>
</div>

<div>
<dt>Score delta</dt>
<dt><span className="stigmem-fields__type">adjust ranking</span></dt>
<dd><code>dict[str, float]</code> keyed by result or fact id.</dd>
</div>

<div>
<dt>Fire and forget</dt>
<dt><span className="stigmem-fields__type">audit / observe</span></dt>
<dd><code>None</code>.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Do not register hooks outside the 22-hook surface list.**

`health_check` is a manifest lifecycle callable, not a hook name.

</div>

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

<div className="stigmem-keypoint">

**If a handler calls `ctx.get_audit_emitter()` without declaring `audit.emit`, registration can succeed but the handler will fail with a capability error when the hook fires.**

The v0.9.0a1 `CoreApis` handles are deliberately narrow and
optional. Operators or tests may expose a callable or facade object
behind a capability; plugins should handle `None` or an unexpected
shape explicitly.

</div>

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

For tests that need to replace the process-global registry temporarily:

```python
from stigmem_node.plugins.testing import stigmem_plugins

from example_stigmem_plugin import plugin_manifest


def test_process_registry_fixture() -> None:
    with stigmem_plugins([plugin_manifest()]) as registry:
        assert "example-stigmem-plugin" in registry.registered_plugins()
```

## Startup loading

After installing the plugin package, Stigmem discovers entry points from the `stigmem.plugins` group and registers them during startup. Dependency ordering is deterministic: dependencies listed in `depends_on` register before the dependent plugin, and cycles fail closed.

For local development only:

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=false
```

<div className="stigmem-keypoint">

**That setting emits a security warning and audit metadata. Do not use it in production.**

</div>

## Signing and trust expectations

Production plugin registration requires a verified signing identity.

<div className="stigmem-grid">

<div><h4><code>STIGMEM_PLUGIN_TRUSTED_PUBLISHERS</code></h4><p>Lists accepted signing identities.</p></div>
<div><h4><code>STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS</code></h4><p>Lists explicit audited exceptions.</p></div>
<div><h4>Unsigned plugins rejected</h4><p>When <code>STIGMEM_PLUGIN_SIGNING_REQUIRED=true</code>.</p></div>

</div>

## Author checklist

Before publishing a plugin:

<ol className="stigmem-steps">
<li>Use <code>requires_stigmem="&gt;=0.9.0a1"</code> or a later alpha bound that matches your tested API surface.</li>
<li>Register only stable hook names from the 22-hook surface.</li>
<li>Declare only capabilities your handlers actually use.</li>
<li>Add unit tests for allow, deny, and error paths.</li>
<li>Verify startup discovery through the <code>stigmem.plugins</code> entry point.</li>
<li>Coordinate signing identity and trusted-publisher configuration with the node operator.</li>
</ol>
