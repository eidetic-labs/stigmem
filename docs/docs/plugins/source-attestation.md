---
title: Source Attestation Plugin
sidebar_label: Source Attestation
description: Operator catalog entry for stigmem-plugin-source-attestation.
audience: Operator
---

# Source Attestation Plugin

| Field | Value |
| --- | --- |
| Package | `stigmem-plugin-source-attestation` |
| Current plugin version | `0.1.0` |
| Stigmem compatibility | `stigmem-node>=0.9.0a8,<1.0.0` |
| Enable gate | `STIGMEM_SOURCE_ATTESTATION_ENABLED` |
| Feature record | [`features/source-attestation`](https://github.com/eidetic-labs/stigmem/tree/main/features/source-attestation) |

This experimental plugin adds source identity checks and source-trust recall
signals when installed, registered, and explicitly enabled. Default Stigmem
installs do not load this behavior.

```bash
python -m pip install 'stigmem-plugin-source-attestation>=0.1.0,<2.0.0'
export STIGMEM_SOURCE_ATTESTATION_ENABLED=1
stigmem plugins doctor
```
