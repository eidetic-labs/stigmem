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

## Project Links

- Repository: <https://github.com/eidetic-labs/stigmem>
- Feature record: <https://github.com/eidetic-labs/stigmem/tree/main/features/source-attestation>
- Plugin source: <https://github.com/eidetic-labs/stigmem/tree/main/experimental/source-attestation>
- Issue tracker: <https://github.com/eidetic-labs/stigmem/issues>
