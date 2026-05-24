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
pip install --pre stigmem-node==0.9.0a8 stigmem-plugin-multi-tenant==0.9.0a8
```

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/multi-tenant>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/multi-tenant>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
