# MCP Adapter Changelog

## Unreleased

- Switched the npm publication target to the scoped package
  `@eidetic-labs/stigmem-mcp@0.1.0`, established independent adapter semver,
  and recorded scoped first-publication dry-run evidence.
- Added the `2026-05-24` host UI smoke execution record and narrowed the
  `0.9.0-alpha.8` publication clearance gate to Codex CLI and Claude Code,
  recorded Gemini CLI as GO-WITH-CAVEAT, and retained Continue.dev, Cursor, and
  Zed as unvalidated experimental connector guides.
- Expanded the MCP live-node smoke to validate `recall`, `lint_scope`, canonical
  smoke URIs, session-aware calls, six-tool discovery, and the package-aligned
  server version reported during MCP initialization.
- Added adapter security regressions for adversarial recall framing, malformed
  write rejection before SDK dispatch, and credential-like tool argument
  filtering.
- Recorded npm dry-run evidence, `alpha` dist-tag usage, executable bin
  packaging, and publication disposition for the MCP adapter package.

## 2026-05-21

- Added ADR-020 feature record for the MCP adapter and made this directory the
  canonical location for adapter-specific behavior, evidence, security posture,
  and release status.

## v0.9.0a1

- Tracked the MCP adapter as experimental external adapter surface area with
  package metadata independent from the alpha artifact set.
