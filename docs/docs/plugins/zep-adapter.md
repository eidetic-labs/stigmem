---
title: Zep Adapter
sidebar_label: Zep Adapter
description: Package and operator notes for the experimental Zep adapter.
audience: Operator
---

# Zep Adapter

`stigmem-plugin-zep-adapter` is an experimental, opt-in Python package that
bridges Stigmem facts into Zep session memory and maps Zep extracted facts back
into Stigmem-shaped records.

## Install

```bash
python -m pip install 'stigmem-plugin-zep-adapter>=0.1.0,<2.0.0'
python -m pip install 'stigmem-plugin-zep-adapter[zep]>=0.1.0,<2.0.0'
```

## Enable

Host applications enable the adapter by importing
`stigmem_plugin_zep.StigmemZepAdapter` and calling it for selected sessions.
There is no node-global environment gate in v0.1.0.

## Disable

Remove the package from the host application environment and restart the
process that loads plugins:

```bash
python -m pip uninstall stigmem-plugin-zep-adapter
```

## Test

```bash
python -m pytest experimental/zep-adapter/tests/ -v
```

The test suite uses a mocked Zep client and does not require a live Zep service.

## Security

Session selection, redaction, retention, deduplication, retry, and write policy
remain host-application responsibilities. See the package-local
`experimental/zep-adapter/security.md` and feature record
`features/zep-adapter/security.md`.
