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
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-lazy-instruction-discovery==0.9.0a8
```

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/lazy-instruction-discovery>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/lazy-instruction-discovery>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
