---
id: index
title: Architecture (v0.2)
sidebar_label: Overview
audience: Spec
---

# Architecture (v0.2)

:::note
This describes the v0.2 reference implementation. For the current architecture (including HLC and federation internals) see [v0.5 Architecture](/docs/v0.2/reference/architecture).
:::

The v0.2 node is a simple FastAPI application backed by SQLite. It does not include the federation pull loop, conflict detector, or HLC — those were added in v0.3–v0.5.

## v0.2 components

| Component | Role |
|-----------|------|
| FastAPI app | HTTP API, request validation |
| SQLite | Persistent fact storage |
| Auth layer | API key validation |
