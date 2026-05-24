---
title: Plugin Management
sidebar_label: Plugin Management
description: Operator workflow for installing, trusting, inspecting, auditing, and troubleshooting Stigmem plugins.
audience: Operator
---

# Plugin Management

<p className="stigmem-meta"><span>5 min read</span><span>Node operator</span><span>Plugins · v0.9.0aN</span></p>

<div className="stigmem-lead">

**What this guide covers**

Operator workflow for installing, trusting, inspecting, auditing,
and troubleshooting Stigmem plugins. Plugins are opt-in Python
packages loaded at node startup through the `stigmem.plugins` entry
point group. The default install runs without plugins.

</div>

<div className="stigmem-keypoint">

**Production deployments should keep plugin signing required, pin plugin package versions, and review every declared capability before rollout.**

</div>

For author-facing package structure and examples, see the [Plugin Author Guide](../../guides/plugins/author-guide.md). For security review inputs, see the [Plugin Capability Reference](../../reference/plugin-api/capabilities.md).

## Production workflow

<ol className="stigmem-steps">
<li><strong>Review the package.</strong> Confirm the plugin name, version, declared hooks, declared capabilities, dependencies, and signing identity.</li>
<li><strong>Install the package</strong> into the node environment. Use the same Python environment that runs <code>stigmem</code> so entry point discovery can find the plugin.</li>
<li><strong>Configure signing trust.</strong> Add accepted signing identities to <code>STIGMEM_PLUGIN_TRUSTED_PUBLISHERS</code>. Use the override list only for explicit, documented exceptions.</li>
<li><strong>Restart the node.</strong> Plugin discovery and registration are startup-only. There is no hot reload or runtime unload path in v0.9.0aN.</li>
<li><strong>Inspect registration and health.</strong> Use <code>stigmem plugins list</code> and <code>stigmem plugins describe</code>.</li>
<li><strong>Review audit events.</strong> Confirm registration, trust decision, and any handler denial or error events.</li>
</ol>

## Install a plugin package

For a source checkout:

```bash
python -m pip install /path/to/example-stigmem-plugin
```

For a pinned package:

```bash
python -m pip install 'example-stigmem-plugin==1.0.0'
```

For Docker deployments, build a derived image or otherwise install the plugin package into the container image used by the node. **Avoid installing plugins manually inside a running container; that is not repeatable and will be lost on redeploy.**

The package must expose an entry point in the `stigmem.plugins` group. Stigmem discovers those entry points, calls the manifest factory, resolves plugin dependencies, verifies signing/trust policy, and registers handlers during startup.

## Configure signing and trust

Production defaults are fail closed:

<div className="stigmem-fields">

<div>
<dt>Setting</dt>
<dt><span className="stigmem-fields__type">Production value</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>STIGMEM_PLUGIN_SIGNING_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type"><code>true</code></span></dt>
<dd>Reject unsigned or unverified plugins during startup registration.</dd>
</div>

<div>
<dt><code>STIGMEM_PLUGIN_TRUSTED_PUBLISHERS</code></dt>
<dt><span className="stigmem-fields__type">comma list</span></dt>
<dd>Allow plugins signed by known publishers.</dd>
</div>

<div>
<dt><code>STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS</code></dt>
<dt><span className="stigmem-fields__type">empty by default</span></dt>
<dd>Explicit audited exception list for signing identities not in the allowlist.</dd>
</div>

</div>

Example:

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=true
STIGMEM_PLUGIN_TRUSTED_PUBLISHERS=builder@example.com,release-bot@example.com
STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS=
```

Use `STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS` only when you have a documented operational reason to accept a specific signing identity outside the normal allowlist. Override registration remains audit-visible with `trust_decision=operator_override`.

### Development-only unsigned loading

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=false
```

<div className="stigmem-keypoint">

**Do not use this in production.**

When disabled, unsigned plugin loading is warning-visible in logs
and audit-visible with `trust_decision=development_unsigned_override`.

</div>

## Inspect installed plugins

```bash
stigmem plugins list
```

Example output:

```text
example-stigmem-plugin 1.0.0 hooks=2 health=healthy signed_by=builder@example.com
```

For machine-readable output:

```bash
stigmem plugins list --json
```

Search the published plugin catalog:

```bash
stigmem plugins search tenant
```

Print install and enable commands for a known plugin:

```bash
stigmem plugins enable multi-tenant
```

Diagnose installed/enabled mismatches:

```bash
stigmem plugins doctor
stigmem doctor
```

Describe one plugin:

```bash
stigmem plugins describe example-stigmem-plugin
```

The describe command reports plugin name and version, signing identity, declared capabilities, registered hooks, dependencies, discovery source, and latest health status, message, and error summary when available.

## Health checks

`health_check` is a lifecycle callable on `PluginManifest`, not a hook. The operator CLI polls plugin health when listing or describing plugins. **Health is informational in v0.9.0aN: unhealthy plugins remain registered and their handlers stay active until a future policy layer changes that behavior.**

<div className="stigmem-fields">

<div>
<dt>Status</dt>
<dt><span className="stigmem-fields__type">Meaning</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>healthy</code></dt>
<dt><span className="stigmem-fields__type">normal</span></dt>
<dd>Plugin reports normal operation.</dd>
</div>

<div>
<dt><code>degraded</code></dt>
<dt><span className="stigmem-fields__type">partial</span></dt>
<dd>Plugin reports partial functionality or a recoverable problem.</dd>
</div>

<div>
<dt><code>unhealthy</code></dt>
<dt><span className="stigmem-fields__type">serious</span></dt>
<dd>Plugin reports a serious problem.</dd>
</div>

<div>
<dt><code>unknown</code></dt>
<dt><span className="stigmem-fields__type">no signal</span></dt>
<dd>No health check is available or health has not been reported.</dd>
</div>

</div>

## Audit events to watch

Plugin registration and handler outcomes are written as audit events. Query audit data through your normal audit pipeline. For the admin audit API, see [Audit & Quotas](../../security/audit-and-quotas.md).

<div className="stigmem-fields">

<div>
<dt>Event type</dt>
<dt><span className="stigmem-fields__type">Trigger</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>plugin.registered</code></dt>
<dt><span className="stigmem-fields__type">success</span></dt>
<dd>A plugin registered successfully. Metadata includes plugin name, hooks, capabilities, discovery source, signing identity, and trust decision when available.</dd>
</div>

<div>
<dt><code>plugin.registration_failed</code></dt>
<dt><span className="stigmem-fields__type">failure</span></dt>
<dd>Registration failed: duplicate names, manifest validation, config validation, dependency, signing, or trust policy problems.</dd>
</div>

<div>
<dt><code>plugin.handler_denied</code></dt>
<dt><span className="stigmem-fields__type">veto</span></dt>
<dd>A voting hook returned <code>Deny</code>. Metadata includes hook, handler name, plugin name, and reason.</dd>
</div>

<div>
<dt><code>plugin.handler_error</code></dt>
<dt><span className="stigmem-fields__type">exception</span></dt>
<dd>A handler raised an exception. Metadata includes hook, handler name, plugin name, error type, and error summary.</dd>
</div>

</div>

**For production alerts, watch for:**

<div className="stigmem-grid">

<div><h4>Any <code>registration_failed</code></h4><p>During deploy.</p></div>
<div><h4>Any <code>development_unsigned_override</code></h4><p>Trust decision.</p></div>
<div><h4><code>operator_override</code> w/o change record</h4><p>Without an approved change record.</p></div>
<div><h4>Repeated <code>handler_error</code></h4></div>
<div><h4>Unexpected capability additions</h4><p>After a plugin upgrade.</p></div>

</div>

## Troubleshooting

<div className="stigmem-fields">

<div>
<dt>Symptom</dt>
<dt><span className="stigmem-fields__type">Likely cause</span></dt>
<dd>Response</dd>
</div>

<div>
<dt><code>No plugins registered</code></dt>
<dt><span className="stigmem-fields__type">discovery miss</span></dt>
<dd>Confirm the package is installed in the same environment as <code>stigmem</code>; verify the package declares <code>[project.entry-points."stigmem.plugins"]</code>; restart the node.</dd>
</div>

<div>
<dt>Startup fails: <code>unsigned</code> plugin</dt>
<dt><span className="stigmem-fields__type">signing required</span></dt>
<dd>Use a signed package from a trusted publisher. Disable signing only in local development.</dd>
</div>

<div>
<dt>Startup fails: <code>signed by untrusted identity</code></dt>
<dt><span className="stigmem-fields__type">not in allowlist</span></dt>
<dd>Add the identity to the trusted-publisher list after review, or use the override list for a documented exception.</dd>
</div>

<div>
<dt>Startup fails: duplicate plugin name</dt>
<dt><span className="stigmem-fields__type">collision</span></dt>
<dd>Remove one package or upgrade to packages with unique names.</dd>
</div>

<div>
<dt>Startup fails: missing dependency</dt>
<dt><span className="stigmem-fields__type">depends_on</span></dt>
<dd>Install the dependency plugin or remove the dependent plugin.</dd>
</div>

<div>
<dt>Handler fails: <code>CapabilityError</code></dt>
<dt><span className="stigmem-fields__type">capability mismatch</span></dt>
<dd>Treat as a plugin bug. Upgrade, disable, or request a corrected manifest.</dd>
</div>

<div>
<dt>Health <code>degraded</code> / <code>unhealthy</code></dt>
<dt><span className="stigmem-fields__type">plugin reported</span></dt>
<dd>Run <code>stigmem plugins describe &lt;name&gt; --json</code>; review <code>health_message</code> and <code>health_error</code>; check plugin logs and audit events.</dd>
</div>

</div>

## Upgrade and rollback checklist

Before upgrading a plugin:

<ol className="stigmem-steps">
<li>Read the release notes and compare the new manifest to the old one.</li>
<li>Review added hooks and capabilities.</li>
<li>Confirm the signing identity is expected.</li>
<li>Deploy first in a non-production environment with production-like signing settings.</li>
<li>Capture <code>stigmem plugins describe &lt;name&gt; --json</code> before and after the upgrade.</li>
</ol>

<div className="stigmem-keypoint">

**To roll back, reinstall the previous pinned plugin version and restart the node.**

Because registration is startup-only, a restart is required for the
old handlers to replace the new ones.

</div>
