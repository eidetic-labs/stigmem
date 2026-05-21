---
feature_id: mcp-adapter
title: MCP adapter
status: active
stability: experimental
since: 0.9.0a1
owner: maintainers
feature_type: adapter
default_surface: external
canonical_spec: none
implementation_path: adapters/mcp
package: stigmem-mcp
adr_refs:
  - ADR-002
  - ADR-009
  - ADR-020
security_refs:
  - R-05
  - R-15
  - R-21
release_lines:
  - v0.9.0a1
  - 0.9.xA
---

# MCP Adapter

The MCP adapter exposes a running Stigmem node as Model Context Protocol tools
for agent hosts such as Claude Code, Codex CLI, Cursor, Zed, and Continue.dev.
It is a stateless TypeScript adapter that translates MCP tool calls into HTTP
requests against the configured node.

The adapter source is active and tested, but the `stigmem-mcp` package version
remains independent from the alpha artifact set. Release-line alignment and
promotion depend on adapter security, packaging, and host-connector validation.

## Current State

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| Default surface | `external` |
| Primary implementation | `adapters/mcp` |
| Primary package | `stigmem-mcp` |
| Canonical spec | `none` |

## Feature Files

- [Spec](./spec.md)
- [Status](./status.md)
- [Evidence](./evidence.md)
- [Security](./security.md)
- [Changelog](./changelog.md)
