---
title: Plugin Management
sidebar_label: Plugin Management
description: Operator workflow for installing, trusting, inspecting, auditing, and troubleshooting Stigmem plugins.
audience: Operator
---

# Plugin Management

**Audience:** Stigmem node operators responsible for enabling and auditing plugins.

Plugins are opt-in Python packages loaded at node startup through the `stigmem.plugins` entry point group. The default install runs without plugins. Production deployments should keep plugin signing required, pin plugin package versions, and review every declared capability before rollout.

For author-facing package structure and examples, see the [Plugin Author Guide](../../guides/plugins/author-guide.md). For security review inputs, see the [Plugin Capability Reference](../../reference/plugin-api/capabilities.md).

## Production workflow

1. **Review the package.** Confirm the plugin name, version, declared hooks, declared capabilities, dependencies, and signing identity.
2. **Install the package into the node environment.** Use the same Python environment that runs `stigmem` so entry point discovery can find the plugin.
3. **Configure signing trust.** Add accepted signing identities to `STIGMEM_PLUGIN_TRUSTED_PUBLISHERS`. Use the override list only for explicit, documented exceptions.
4. **Restart the node.** Plugin discovery and registration are startup-only. There is no hot reload or runtime unload path in v0.9.0aN.
5. **Inspect registration and health.** Use `stigmem plugins list` and `stigmem plugins describe`.
6. **Review audit events.** Confirm registration, trust decision, and any handler denial or error events.

## Install a plugin package

Install plugins the same way you install other Python packages in the node runtime.

For a source checkout:

```bash
python -m pip install /path/to/example-stigmem-plugin
```

For a pinned package:

```bash
python -m pip install 'example-stigmem-plugin==1.0.0'
```

For Docker deployments, build a derived image or otherwise install the plugin package into the container image used by the node. Avoid installing plugins manually inside a running container; that is not repeatable and will be lost on redeploy.

The package must expose an entry point in the `stigmem.plugins` group. Stigmem discovers those entry points, calls the manifest factory, resolves plugin dependencies, verifies signing/trust policy, and registers handlers during startup.

## Configure signing and trust

Production defaults are fail closed:

| Setting | Production value | Purpose |
|---|---|---|
| `STIGMEM_PLUGIN_SIGNING_REQUIRED` | `true` | Reject unsigned or unverified plugins during startup registration. |
| `STIGMEM_PLUGIN_TRUSTED_PUBLISHERS` | Comma-separated signing identities | Allow plugins signed by known publishers. |
| `STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS` | Empty by default | Explicit audited exception list for signing identities that are not in the trusted-publisher allowlist. |

Example:

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=true
STIGMEM_PLUGIN_TRUSTED_PUBLISHERS=builder@example.com,release-bot@example.com
STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS=
```

Use `STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS` only when you have a documented operational reason to accept a specific signing identity outside the normal allowlist. Override registration remains audit-visible with `trust_decision=operator_override`.

### Development-only unsigned loading

Local development can load unsigned plugins by setting:

```bash
STIGMEM_PLUGIN_SIGNING_REQUIRED=false
```

Do not use this in production. When disabled, unsigned plugin loading is warning-visible in logs and audit-visible with `trust_decision=development_unsigned_override`.

## Inspect installed plugins

List registered plugins:

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

Describe one plugin:

```bash
stigmem plugins describe example-stigmem-plugin
```

The describe command reports:

- plugin name and version,
- signing identity,
- declared capabilities,
- registered hooks,
- dependencies,
- discovery source,
- latest health status, message, and error summary when available.

## Health checks

`health_check` is a lifecycle callable on `PluginManifest`, not a hook. The operator CLI polls plugin health when listing or describing plugins. Health is informational in v0.9.0aN: unhealthy plugins remain registered and their handlers stay active until a future policy layer changes that behavior.

Health statuses are:

| Status | Meaning |
|---|---|
| `healthy` | The plugin reports normal operation. |
| `degraded` | The plugin reports partial functionality or a recoverable problem. |
| `unhealthy` | The plugin reports a serious problem. |
| `unknown` | No health check is available or health has not been reported. |

## Audit events to watch

Plugin registration and handler outcomes are written as audit events. Query audit data through your normal audit pipeline. For the admin audit API, see [Audit & Quotas](../../security/audit-and-quotas.md).

Important event types:

| Event type | Meaning |
|---|---|
| `plugin.registered` | A plugin registered successfully. Metadata includes plugin name, hooks, capabilities, discovery source, signing identity, and trust decision when available. |
| `plugin.registration_failed` | Registration failed because of duplicate names, manifest validation, config validation, dependency, signing, or trust policy problems. |
| `plugin.handler_denied` | A voting hook returned `Deny`. Metadata includes hook, handler name, plugin name, and reason. |
| `plugin.handler_error` | A handler raised an exception. Metadata includes hook, handler name, plugin name, error type, and error summary. |

For production alerts, watch for:

- any `plugin.registration_failed` event during deploy,
- any `development_unsigned_override` trust decision,
- any `operator_override` trust decision without an approved change record,
- repeated `plugin.handler_error` events,
- unexpected capability additions after a plugin upgrade.

## Troubleshooting

| Symptom | Likely cause | Response |
|---|---|---|
| `No plugins registered` | Package is not installed in the node environment, entry point group is missing, or discovery found no packages. | Confirm the package is installed in the same environment as `stigmem`; verify the package declares `[project.entry-points."stigmem.plugins"]`; restart the node. |
| Startup fails with `unsigned` plugin error | `STIGMEM_PLUGIN_SIGNING_REQUIRED=true` and the plugin did not arrive with verified signing metadata. | Use a signed package from a trusted publisher. Disable signing only in local development. |
| Startup fails with `signed by untrusted identity` | The signing identity is not in `STIGMEM_PLUGIN_TRUSTED_PUBLISHERS` or the explicit override list. | Add the identity to the trusted-publisher list after review, or use the override list for a documented exception. |
| Startup fails with duplicate plugin name | Two discovered packages return the same `PluginManifest.name`. | Remove one package or upgrade to packages with unique names. |
| Startup fails with missing plugin dependency | A plugin lists `depends_on` entries that are not installed or already registered. | Install the dependency plugin or remove the dependent plugin. |
| Handler fails with `CapabilityError` | The plugin called a `PluginContext` accessor without declaring the matching capability. | Treat this as a plugin bug. Upgrade, disable, or request a corrected manifest. |
| Health is `degraded` or `unhealthy` | The plugin health check reported a problem, or raised an exception. | Run `stigmem plugins describe <name> --json`; review `health_message` and `health_error`; check plugin logs and audit events. |

## Upgrade and rollback checklist

Before upgrading a plugin:

- Read the release notes and compare the new manifest to the old one.
- Review added hooks and capabilities.
- Confirm the signing identity is expected.
- Deploy first in a non-production environment with production-like signing settings.
- Capture `stigmem plugins describe <name> --json` before and after the upgrade.

To roll back, reinstall the previous pinned plugin version and restart the node. Because registration is startup-only, a restart is required for the old handlers to replace the new ones.
