# Stigmem Lazy Instruction Discovery Plugin

Experimental lazy instruction discovery plugin for Stigmem.

This package provides the `stigmem-plugin-lazy-instruction-discovery` source
package for alpha validation. It registers through the `stigmem.plugins` entry
point group and is loaded by `stigmem-node` when explicitly installed and
configured by an operator.

## Status

Lazy instruction discovery remains experimental. Installing this package does
not graduate the feature into the supported default surface. Default Stigmem
installs do not expose lazy-instruction routes unless the plugin is registered
and configured.

Use this package only in isolated alpha or evaluation environments. The package
metadata is publication-shaped for the plugin readiness track, but registry
publication remains on hold until dry-run evidence and maintainer clearance are
recorded. See the feature record under `features/lazy-instruction-discovery/`
for the current status, evidence, and security notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-lazy-instruction-discovery==0.1.0
```

## Enable

Set the plugin gate environment variable to opt in:

```bash
export STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED=1
```

The default install is inert; lazy instruction discovery only activates when
the package is installed, discovered through the `stigmem.plugins` entry point,
and the operator enables the gate. Manifest publication, instruction recall,
and file-path entries remain separately gated.

## Disable

Unset the plugin gate environment variable, or set it to any value other than
`1`, `true`, `yes`, or `on`:

```bash
unset STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED
```

The plugin returns to inert state at the next process start. No data migration
is required; core instruction-channel, scope, tenant, and audit enforcement
continues to hold.

## Test

From a Stigmem repository checkout with development dependencies installed:

```bash
uv run pytest node/tests/plugins/test_lazy_instruction_plugin_scaffold.py \
  node/tests/plugins/test_lazy_instruction_plugin_integration.py
```

The package itself ships no separate test tree; upstream plugin validation
lives in `node/tests/plugins/`.

## Uninstall

```bash
pip uninstall stigmem-plugin-lazy-instruction-discovery
```

Removing the package is sufficient. The gate environment variable becomes moot
once the entry point is no longer discoverable.

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/lazy-instruction-discovery>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/lazy-instruction-discovery>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
