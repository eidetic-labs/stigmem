---
title: CLI Reference
sidebar_label: CLI
sidebar_position: 0
description: Command-line interface reference for the Stigmem node binaries.
audience: Operator
---

# CLI Reference

*Audience: node operators and developers running or administering a Stigmem node.*

The Stigmem package provides two CLI entry points:

| Command | Purpose |
|---------|---------|
| [`stigmem`](./stigmem) | Management CLI — capability tokens, federation, snapshots, decay, instructions, audit, identity, CID backfill |
| [`stigmem-node`](./stigmem-node) | Start the Stigmem HTTP server (FastAPI + uvicorn) |

These pages are auto-generated from `--help` output. Regenerate after CLI changes with:

```bash
make gen-cli-docs
```
