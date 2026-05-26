---
title: Letta Adapter
sidebar_label: Letta Adapter
description: Experimental Letta archival-memory adapter plugin.
audience: Operator
---

# Letta Adapter

`stigmem-plugin-letta-adapter` bridges selected Stigmem facts into a Letta
agent's archival memory and reads tagged passages back as Stigmem-compatible
records.

## Install

```bash
python -m pip install 'stigmem-plugin-letta-adapter>=0.1.0,<2.0.0'
```

Install the live Letta extra only in host applications that call a Letta server:

```bash
python -m pip install 'stigmem-plugin-letta-adapter[letta]>=0.1.0,<2.0.0'
```

## Enable

The adapter has no node-global behavior gate at v0.1.0. Enable it in the host
application by importing `stigmem_plugin_letta.StigmemLettaAdapter` and calling
the bridge methods explicitly.

## Disable

Remove the adapter from the host application path and restart the process that
loads plugins. If it was installed only for this integration, uninstall it:

```bash
python -m pip uninstall stigmem-plugin-letta-adapter
```

## Security Notes

The adapter can send fact content, scope labels, source identifiers, and
confidence values to a configured Letta server and target agent. Live Letta use
is operator-owned for v0.1.0; review
`experimental/letta-adapter/security.md` before using it with sensitive scopes.
