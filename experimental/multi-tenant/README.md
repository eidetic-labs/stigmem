# Stigmem Multi-Tenant Plugin

Experimental multi-tenant scoping plugin for Stigmem.

This package provides the `stigmem-plugin-multi-tenant` source package for
alpha validation. It registers through the `stigmem.plugins` entry point group
and is loaded by `stigmem-node` only when explicitly installed and configured by
an operator.

## Status

Multi-tenant scoping remains experimental. Installing this package does not add
shared-node readiness to the supported default surface. Default installs
collapse callers into the `default` tenant unless the plugin is registered and
`STIGMEM_MULTI_TENANT_ENABLED=true`.

The package metadata is publication-shaped for the plugin readiness track, but
registry publication remains on hold until dry-run evidence and maintainer
clearance are recorded. See the feature record under `features/multi-tenant/`
for the current status, evidence, and security notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-multi-tenant==0.1.0
```

## Enable

Set the plugin gate environment variable to opt in:

```bash
export STIGMEM_MULTI_TENANT_ENABLED=1
```

The default install is inert; multi-tenant hook behavior only activates when
the package is installed, discovered through the `stigmem.plugins` entry point,
and the operator enables the gate. Until then callers continue to collapse into
the core `default` tenant boundary.

## Disable

Unset the plugin gate environment variable, or set it to any value other than
`1`, `true`, `yes`, or `on`:

```bash
unset STIGMEM_MULTI_TENANT_ENABLED
```

The plugin returns to inert state at the next process start. No data migration
is required; core tenant, scope, and audit isolation continues to hold.

## Test

From a Stigmem repository checkout with development dependencies installed:

```bash
uv run pytest node/tests/plugins/test_multi_tenant_plugin_scaffold.py \
  node/tests/plugins/test_multi_tenant_plugin_validation.py
```

The package itself ships no separate test tree; upstream plugin validation
lives in `node/tests/plugins/`.

## Uninstall

```bash
pip uninstall stigmem-plugin-multi-tenant
```

Removing the package is sufficient. The gate environment variable becomes moot
once the entry point is no longer discoverable.

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/multi-tenant>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/multi-tenant>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
