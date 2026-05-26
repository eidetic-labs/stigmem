---
title: Plugin Catalog
sidebar_label: Catalog
description: Published experimental Stigmem plugins and their operator gates.
audience: Operator
---

# Plugin Catalog

Stigmem plugins are optional Python packages discovered through the
`stigmem.plugins` entry point group. Installing a plugin package makes it
discoverable. Node behavior plugins still require the plugin's explicit
`STIGMEM_*_ENABLED` gate and a node restart; adapter packages require
host-application opt-in.

The eleven plugins below are independently versioned at `0.1.0` and support the
current alpha node line. The adapter-batch packages require
`stigmem-node>=0.9.0a10,<1.0.0`; earlier security plugins support the alpha
line they were published on. They remain experimental and opt-in.

| Plugin | Package | Enable gate | Summary |
| --- | --- | --- | --- |
| [Lazy instruction discovery](./lazy-instruction-discovery.md) | `stigmem-plugin-lazy-instruction-discovery` | `STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED` | Instruction manifest discovery and migration helpers. |
| [Time travel](./time-travel.md) | `stigmem-plugin-time-travel` | `STIGMEM_TIME_TRAVEL_ENABLED` | Historical fact and recall query behavior. |
| [Tombstones](./tombstones.md) | `stigmem-plugin-tombstones` | `STIGMEM_TOMBSTONES_ENABLED` | Right-to-be-forgotten tombstone enforcement. |
| [Memory Garden ACL](./memory-garden-acl.md) | `stigmem-plugin-memory-garden-acl` | `STIGMEM_MEMORY_GARDEN_ACL_ENABLED` | Memory Garden membership ACL filtering. |
| [Source attestation](./source-attestation.md) | `stigmem-plugin-source-attestation` | `STIGMEM_SOURCE_ATTESTATION_ENABLED` | Source identity checks and source-trust recall signals. |
| [Multi-tenant scoping](./multi-tenant.md) | `stigmem-plugin-multi-tenant` | `STIGMEM_MULTI_TENANT_ENABLED` | Tenant scoping and default-tenant collapse. |
| [Cognee adapter](./cognee-adapter.md) | `stigmem-plugin-cognee-adapter` | Host-application opt-in | Bridges selected facts into Cognee memory graphs. |
| [Gemini adapter](./gemini-adapter.md) | `stigmem-plugin-gemini-adapter` | Host-application opt-in | Exposes Stigmem tools as Gemini FunctionDeclarations. |
| [Letta adapter](./letta-adapter.md) | `stigmem-plugin-letta-adapter` | Host-application opt-in | Bridges selected facts into Letta archival memory. |
| [OpenAI tools adapter](./openai-tools-adapter.md) | `stigmem-plugin-openai-tools-adapter` | Host-application opt-in | Exposes Stigmem tools as OpenAI-compatible function calls. |
| [Zep adapter](./zep-adapter.md) | `stigmem-plugin-zep-adapter` | Host-application opt-in | Bridges selected facts into Zep session memory. |

## Install

Install one plugin:

```bash
python -m pip install 'stigmem-plugin-tombstones>=0.1.0,<2.0.0'
export STIGMEM_TOMBSTONES_ENABLED=1
```

Install through the meta-package extras:

```bash
python -m pip install --pre 'stigmem[tombstones]'
python -m pip install --pre 'stigmem[plugins-all]'
```

After installing or changing an enable gate, restart the node and run:

```bash
stigmem plugins list
stigmem plugins doctor
```

For package trust, signing, and operational review, see
[Plugin Management](../operators/plugins/management.md).
