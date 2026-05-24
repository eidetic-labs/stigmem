# MCP Adapter Changelog

## Unreleased

- Expanded the MCP live-node smoke to validate `recall`, `lint_scope`, canonical
  smoke URIs, session-aware calls, six-tool discovery, and the package-aligned
  server version reported during MCP initialization.
- Aligned `stigmem-mcp` package metadata to the current alpha release line for
  publication readiness while keeping registry publication held pending live
  connector smoke, security certification, dry-run evidence, and maintainer
  clearance.

## 2026-05-21

- Added ADR-020 feature record for the MCP adapter and made this directory the
  canonical location for adapter-specific behavior, evidence, security posture,
  and release status.

## v0.9.0a1

- Tracked the MCP adapter as experimental external adapter surface area with
  package metadata independent from the alpha artifact set.
