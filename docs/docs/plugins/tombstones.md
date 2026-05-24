---
title: Tombstones Plugin
sidebar_label: Tombstones
description: Operator catalog entry for stigmem-plugin-tombstones.
audience: Operator
---

# Tombstones Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-tombstones` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a8,<1.0.0` |
| Enable gate | `STIGMEM_TOMBSTONES_ENABLED` |
| Feature record | [`features/tombstones`](https://github.com/eidetic-labs/stigmem/tree/main/features/tombstones) |

This experimental plugin adds right-to-be-forgotten tombstone enforcement when
installed, registered, and explicitly enabled. Default Stigmem installs do not
load this behavior.

```bash
python -m pip install 'stigmem-plugin-tombstones>=0.1.0,<2.0.0'
export STIGMEM_TOMBSTONES_ENABLED=1
stigmem plugins doctor
```
