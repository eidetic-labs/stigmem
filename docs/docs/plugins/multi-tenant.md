---
title: Multi-Tenant Scoping Plugin
sidebar_label: Multi-Tenant Scoping
description: Operator catalog entry for stigmem-plugin-multi-tenant.
audience: Operator
---

# Multi-Tenant Scoping Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-multi-tenant` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a9,<1.0.0` |
| Enable gate | `STIGMEM_MULTI_TENANT_ENABLED` |
| Feature record | [`features/multi-tenant`](https://github.com/eidetic-labs/stigmem/tree/main/features/multi-tenant) |

This experimental plugin adds tenant scoping and default-tenant collapse when
installed, registered, and explicitly enabled. Default Stigmem installs
continue to resolve callers into the `default` tenant.

```bash
python -m pip install 'stigmem-plugin-multi-tenant>=0.1.0,<2.0.0'
export STIGMEM_MULTI_TENANT_ENABLED=1
stigmem plugins doctor
```
