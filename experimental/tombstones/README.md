# Stigmem Tombstones Plugin

Experimental right-to-be-forgotten tombstones plugin for Stigmem.

This package provides the `stigmem-plugin-tombstones` source package for alpha
validation. It registers through the `stigmem.plugins` entry point group and is
loaded by `stigmem-node` only when explicitly installed and configured by an
operator.

## Status

Tombstones remain experimental. Installing this package does not add tombstone
filtering or propagation to the supported default surface. Default Stigmem
installs keep tombstone behavior disabled unless the plugin is registered and
the operator enables the relevant gates.

The package metadata is publication-shaped for the plugin readiness track, but
registry publication remains on hold until dry-run evidence and maintainer
clearance are recorded. See the feature record under `features/tombstones/` for
the current status, evidence, and security notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-tombstones==0.9.0a8
```

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/tombstones>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/tombstones>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
