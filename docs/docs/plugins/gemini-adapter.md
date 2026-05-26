---
title: Gemini Adapter
sidebar_label: Gemini Adapter
description: Experimental Gemini FunctionDeclaration adapter plugin.
audience: Operator
---

# Gemini Adapter

`stigmem-plugin-gemini-adapter` exposes Stigmem fact, query, contradiction,
subscription, and lint operations as Gemini-native `FunctionDeclaration`
dictionaries.

## Install

```bash
python -m pip install 'stigmem-plugin-gemini-adapter>=0.1.0,<2.0.0'
```

Install the live Gemini SDK extra only in host applications that call the
convenience `run()` loop:

```bash
python -m pip install 'stigmem-plugin-gemini-adapter[gemini]>=0.1.0,<2.0.0'
```

## Enable

The adapter has no node-global behavior gate at v0.1.0. Enable it in the host
application by importing `stigmem_plugin_gemini.StigmemGeminiAdapter` and
passing its declarations to Gemini.

## Disable

Remove the adapter from the host application path and restart the process that
loads plugins. If it was installed only for this integration, uninstall it:

```bash
python -m pip uninstall stigmem-plugin-gemini-adapter
```

## Security Notes

The adapter can send tool declarations, tool arguments, source identifiers,
scope labels, and model-loop results through a host application's Gemini
integration. Live Gemini use is operator-owned for v0.1.0; review
`experimental/gemini-adapter/security.md` before using it with sensitive scopes.
