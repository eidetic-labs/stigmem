# Stigmem Time-Travel Plugin

Experimental time-travel query plugin for Stigmem.

This package provides the `stigmem-plugin-time-travel` source package for alpha
validation. It registers through the `stigmem.plugins` entry point group and is
loaded by `stigmem-node` only when explicitly installed and configured by an
operator.

## Status

Time-travel queries remain experimental. Installing this package does not add
historical query behavior to the supported default surface. Default Stigmem
installs reject `as_of` requests unless the plugin is registered and the
operator enables the relevant gates.

The package metadata is publication-shaped for the plugin readiness track, but
registry publication remains on hold until dry-run evidence and maintainer
clearance are recorded. See the feature record under `features/time-travel/`
for the current status, evidence, and security notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-time-travel==0.1.0
```

## Enable

Set the plugin gate environment variable to opt in:

```bash
export STIGMEM_TIME_TRAVEL_ENABLED=1
```

The default install is inert; time-travel hook behavior only activates when the
package is installed, discovered through the `stigmem.plugins` entry point, and
the operator enables the gate. Fact-query and recall `as_of` paths remain
separately gated by `STIGMEM_TIME_TRAVEL_ALLOW_FACT_QUERY_AS_OF` and
`STIGMEM_TIME_TRAVEL_ALLOW_RECALL_AS_OF`.

## Disable

Unset the plugin gate environment variable, or set it to any value other than
`1`, `true`, `yes`, or `on`:

```bash
unset STIGMEM_TIME_TRAVEL_ENABLED
```

The plugin returns to inert state at the next process start. No data migration
is required; core scope, tenant, and audit enforcement continues to hold.

## Test

From a Stigmem repository checkout with development dependencies installed:

```bash
uv run pytest node/tests/plugins/test_time_travel_plugin_scaffold.py \
  node/tests/plugins/test_time_travel_plugin_validation.py
```

The package itself ships no separate test tree; upstream plugin validation
lives in `node/tests/plugins/`.

## Uninstall

```bash
pip uninstall stigmem-plugin-time-travel
```

Removing the package is sufficient. The gate environment variable becomes moot
once the entry point is no longer discoverable.

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/time-travel>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/time-travel>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
