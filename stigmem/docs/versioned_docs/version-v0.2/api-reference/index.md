---
id: index
title: API Reference (v0.2)
sidebar_label: Overview
---

# API Reference (v0.2)

:::note
This documents the v0.2 wire format. The v0.2 API is a subset of the current v0.5 API — no HLC fields, no federation endpoints, no conflict endpoints.
:::

## Endpoints in v0.2

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/facts` | Assert a fact |
| GET | `/v1/facts` | Query facts |
| GET | `/.well-known/stigmem` | Node metadata |

See the [v0.5 API reference](/docs/api-reference) for the full current endpoint set.
