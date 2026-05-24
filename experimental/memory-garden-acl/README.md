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

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/memory-garden-acl>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/memory-garden-acl>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
