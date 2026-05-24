---
title: Time Travel Plugin
sidebar_label: Time Travel
description: Operator catalog entry for stigmem-plugin-time-travel.
audience: Operator
---

# Time Travel Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-time-travel` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a8,<1.0.0` |
| Enable gate | `STIGMEM_TIME_TRAVEL_ENABLED` |
| Feature record | [`features/time-travel`](https://github.com/eidetic-labs/stigmem/tree/main/features/time-travel) |

This experimental plugin adds historical fact and recall query behavior when
installed, registered, and explicitly enabled. Default Stigmem installs do not
load this behavior.

```bash
python -m pip install 'stigmem-plugin-time-travel>=0.1.0,<2.0.0'
export STIGMEM_TIME_TRAVEL_ENABLED=1
stigmem plugins doctor
```
