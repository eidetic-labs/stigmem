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

Use this package only in isolated alpha or evaluation environments. See
`STATUS.md` and `security.md` in the source repository for the ADR-008 gate
status and feature-owned security notes.

## Installation

```bash
pip install --pre stigmem-node==0.9.0a2 stigmem-plugin-lazy-instruction-discovery==0.9.0a2
```

## Project Links

- Repository: <https://github.com/Eidetic-Labs/stigmem>
- Plugin source: <https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/lazy-instruction-discovery>
- Issue tracker: <https://github.com/Eidetic-Labs/stigmem/issues>
