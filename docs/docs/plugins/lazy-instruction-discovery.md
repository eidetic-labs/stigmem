---
title: Lazy Instruction Discovery Plugin
sidebar_label: Lazy Instruction Discovery
description: Operator catalog entry for stigmem-plugin-lazy-instruction-discovery.
audience: Operator
---

# Lazy Instruction Discovery Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-lazy-instruction-discovery` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a8,<1.0.0` |
| Enable gate | `STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED` |
| Feature record | [`features/lazy-instruction-discovery`](https://github.com/eidetic-labs/stigmem/tree/main/features/lazy-instruction-discovery) |

This experimental plugin adds instruction manifest discovery and migration
helpers when installed, registered, and explicitly enabled. Default Stigmem
installs do not load this behavior.

```bash
python -m pip install 'stigmem-plugin-lazy-instruction-discovery>=0.1.0,<2.0.0'
export STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED=1
stigmem plugins doctor
```
