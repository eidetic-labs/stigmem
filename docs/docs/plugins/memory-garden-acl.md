---
title: Memory Garden ACL Plugin
sidebar_label: Memory Garden ACL
description: Operator catalog entry for stigmem-plugin-memory-garden-acl.
audience: Operator
---

# Memory Garden ACL Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-memory-garden-acl` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a8,<1.0.0` |
| Enable gate | `STIGMEM_MEMORY_GARDEN_ACL_ENABLED` |
| Feature record | [`features/memory-garden-acl`](https://github.com/eidetic-labs/stigmem/tree/main/features/memory-garden-acl) |

This experimental plugin adds Memory Garden membership ACL filtering when
installed, registered, and explicitly enabled. Default Stigmem installs do not
load this behavior.

```bash
python -m pip install 'stigmem-plugin-memory-garden-acl>=0.1.0,<2.0.0'
export STIGMEM_MEMORY_GARDEN_ACL_ENABLED=1
stigmem plugins doctor
```
