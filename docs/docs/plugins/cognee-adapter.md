---
title: Cognee Adapter Plugin
sidebar_label: Cognee Adapter
description: Operator catalog entry for stigmem-plugin-cognee-adapter.
audience: Operator
---

# Cognee Adapter Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-cognee-adapter` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a10,<1.0.0` |
| Enable gate | Host-application opt-in |
| Feature record | [`features/cognee-adapter`](https://github.com/eidetic-labs/stigmem/tree/main/features/cognee-adapter) |

This experimental adapter bridges selected Stigmem facts into Cognee memory
graphs and normalizes Cognee search results back into Stigmem-shaped records.
Installing the package makes the adapter discoverable; the host application
chooses when to call the bridge.

The package does not publish a `cognee` extra in v0.1.0 because Cognee's
current dependency path resolves `diskcache==5.6.3`, which is affected by
CVE-2025-69872 unsafe pickle deserialization. Live Cognee deployments must
install Cognee separately after accepting and mitigating the upstream
cache-directory risk.

```bash
python -m pip install 'stigmem-plugin-cognee-adapter>=0.1.0,<2.0.0'
stigmem plugins doctor
```
