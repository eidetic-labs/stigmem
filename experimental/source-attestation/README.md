# Stigmem Source Attestation Plugin

Experimental source attestation plugin for Stigmem.

This package provides the `stigmem-plugin-source-attestation` source package
for alpha validation. It registers through the `stigmem.plugins` entry point
group and is loaded by `stigmem-node` only when explicitly installed and
configured by an operator.

## Status

Source attestation remains experimental. Installing this package does not add
assertion-source enforcement, recall source weighting, or federation source
guards to the supported default surface. Default installs remain inert unless
the plugin is registered and the operator enables the relevant gates.

The package metadata is publication-shaped for the plugin readiness track, but
registry publication remains on hold until dry-run evidence and maintainer
clearance are recorded. See the feature record under
`features/source-attestation/` for the current status, evidence, and security
notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-source-attestation==0.9.0a8
```

## Enable

Set the plugin gate environment variable to opt in:

```bash
export STIGMEM_SOURCE_ATTESTATION_ENABLED=1
```

The default install is inert; source attestation only activates when the
package is installed, discovered through the `stigmem.plugins` entry point, and
the operator enables the gate. Enforcement-specific gates such as
`STIGMEM_SOURCE_ATTESTATION_ENFORCE_ASSERT_VALIDATION` and
`STIGMEM_SOURCE_ATTESTATION_ENFORCE_FEDERATION_INBOUND` remain opt-in and must
not be enabled with warn-only mode.

## Disable

Unset the plugin gate environment variable, or set it to any value other than
`1`, `true`, `yes`, or `on`:

```bash
unset STIGMEM_SOURCE_ATTESTATION_ENABLED
```

The plugin returns to inert state at the next process start. No data migration
is required; core source, scope, tenant, and audit enforcement continues to hold
without plugin participation.

## Test

From a Stigmem repository checkout with development dependencies installed:

```bash
uv run pytest node/tests/plugins/test_source_attestation_plugin_scaffold.py \
  node/tests/plugins/test_source_attestation_plugin_validation.py
```

The package itself ships no separate test tree; upstream plugin validation
lives in `node/tests/plugins/`.

## Uninstall

```bash
pip uninstall stigmem-plugin-source-attestation
```

Removing the package is sufficient. The gate environment variable becomes moot
once the entry point is no longer discoverable.

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/source-attestation>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/source-attestation>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
