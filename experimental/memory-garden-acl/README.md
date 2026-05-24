# Stigmem Memory Garden Advanced ACL Plugin

Experimental advanced Memory Garden ACL plugin for Stigmem.

This package provides the `stigmem-plugin-memory-garden-acl` source package for
alpha validation. It registers through the `stigmem.plugins` entry point group
and is loaded by `stigmem-node` only when explicitly installed and configured by
an operator.

## Status

Advanced Memory Garden ACL behavior remains experimental. Basic garden CRUD,
membership, and direct garden fact guards remain core. Installing this package
does not activate advanced cross-surface ACL behavior unless the plugin is
registered and the operator enables the relevant gates.

The package metadata is publication-shaped for the plugin readiness track, but
registry publication remains on hold until dry-run evidence and maintainer
clearance are recorded. See the feature record under
`features/memory-garden-acl/` for the current status, evidence, and security
notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-memory-garden-acl==0.9.0a8
```

## Enable

Set the plugin gate environment variable to opt in:

```bash
export STIGMEM_MEMORY_GARDEN_ACL_ENABLED=1
```

The default install is inert; advanced ACL hook behavior only activates when
the package is installed, discovered through the `stigmem.plugins` entry point,
and the operator enables the gate. Enforcement gates such as
`STIGMEM_MEMORY_GARDEN_ACL_ENFORCE_ASSERT_AUTHORIZE` and
`STIGMEM_MEMORY_GARDEN_ACL_ENFORCE_RECALL_AUTHORIZE` remain separately opt-in.

## Disable

Unset the plugin gate environment variable, or set it to any value other than
`1`, `true`, `yes`, or `on`:

```bash
unset STIGMEM_MEMORY_GARDEN_ACL_ENABLED
```

The plugin returns to inert state at the next process start. No data migration
is required; core garden CRUD, membership, scope, tenant, and audit enforcement
continues to hold.

## Test

From a Stigmem repository checkout with development dependencies installed:

```bash
uv run pytest node/tests/plugins/test_memory_garden_acl_plugin_scaffold.py \
  node/tests/plugins/test_memory_garden_acl_plugin_validation.py
```

The package itself ships no separate test tree; upstream plugin validation
lives in `node/tests/plugins/`.

## Uninstall

```bash
pip uninstall stigmem-plugin-memory-garden-acl
```

Removing the package is sufficient. The gate environment variable becomes moot
once the entry point is no longer discoverable.

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/memory-garden-acl>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/memory-garden-acl>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
