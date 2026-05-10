# Reference Boot Stubs — spec §21.1 (v1.0 instruction-discovery design)

This directory contains reference boot stub templates for three adapter profiles.
Each file is a **Markdown document with YAML frontmatter** as specified in §21.1.2.

## Files

| File | Profile | Description |
|---|---|---|
| `claude-code.md` | `paperclip-claude-code` | Claude Code / Paperclip harness |
| `openclaw.md` | `openclaw` | OpenClaw soul/skills adapter |
| `generic-mcp.md` | `generic` | Generic MCP tool-list adapter |

## Usage

Boot stubs are generated automatically by `GET /v1/agents/{agent_id}/boot-stub`.
These templates show the expected structure and can be used as a starting point
for custom deployment overrides.

Replace placeholder values (`{{AGENT_ID}}`, `{{AGENT_ROLE}}`, `{{MANIFEST_URI}}`,
`{{DEPLOYMENT}}`) before use.

## Token Budget

Per §21.1.2 the body section (after frontmatter) MUST be ≤ 500 tokens (cl100k).
The templates below target ≤ 350 tokens to leave headroom for adapter injection.
