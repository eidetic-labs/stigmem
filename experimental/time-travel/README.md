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
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-time-travel==0.9.0a8
```

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/time-travel>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/time-travel>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
