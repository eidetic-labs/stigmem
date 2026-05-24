# MCP Host UI Smoke — 2026-05-24

**Status:** Codex CLI and Claude Code host UI smoke passed for
`0.9.0-alpha.8`; Gemini CLI completed with caveat
**Operator:** Codex CLI, Claude Code, and Gemini CLI smoke run in the
maintainer environment
**stigmem-mcp version:** `0.9.0-alpha.8` on PR branch
`docs/mcp-host-ui-smoke-gate`
**stigmem-node version:** `0.9.0a8` on PR branch
`docs/mcp-host-ui-smoke-gate`
**Date:** 2026-05-24
**Node URL:** `http://127.0.0.1:18765` for Codex CLI smoke;
`http://127.0.0.1:18766` for Claude Code smoke;
`http://127.0.0.1:18767` for Gemini CLI smoke
**API key label:** existing Codex MCP config key, redacted; local smoke node
ran with `STIGMEM_AUTH_REQUIRED=false`, so the key was not required. Claude
Code smoke used a temporary MCP config without `STIGMEM_API_KEY`.
Gemini CLI smoke used a temporary project-scoped `.gemini/settings.json` entry,
then removed it after testing.

This record is the PR-attachable execution artifact for the MCP adapter host UI
smoke gate. It complements the repo-local stdio smoke in
`adapters/mcp/tests/smoke.sh`; it does not replace that automated protocol
coverage.

`0.9.0-alpha.8` narrows the publication clearance claim to Codex CLI, Claude
Code, Gemini CLI with the caveat recorded below, and the repo-local MCP
protocol smoke. Continue.dev, Cursor, and Zed connector guides remain
experimental and unvalidated because those host UIs are not available in the
maintainer environment for this gate. Do not describe those three hosts as
validated in package or release material until a future PR records real host UI
results.

Do not move `stigmem-mcp` from `hold` to a publication-ready disposition until
this file records real host UI PASS, GO-WITH-CAVEAT, or explicit maintainer
NO-GO decisions for the validated publication claim. Maintainer publication
clearance remains a separate action.

## Pre-flight

Run once before testing any editor. The recorded Codex CLI smoke used port
`18765`, the recorded Claude Code smoke used port `18766`, and the recorded
Gemini CLI smoke used port `18767` to avoid clashing with any maintainer-local
node:

```bash
cd ~/Desktop/stigmem
STIGMEM_AUTH_REQUIRED=false \
  STIGMEM_DB_PATH=/private/tmp/stigmem-codex-ui-smoke.db \
  STIGMEM_HOST=127.0.0.1 \
  STIGMEM_PORT=18765 \
  uv run python -c 'from stigmem_node.main import run; run()'
```

Generate or register a smoke-only API key for the local node. Do not use a
production key. If auth is disabled for a loopback-only node, record that fact
instead of fabricating a key label.

Build and install the adapter locally:

```bash
cd ~/Desktop/stigmem/adapters/mcp
pnpm install
pnpm build
chmod +x dist/server.js
npm pack
npm install -g ./stigmem-mcp-0.9.0-alpha.8.tgz
which stigmem-mcp
```

The Codex CLI MCP configuration must reference `stigmem-mcp` or the absolute
path reported by `which stigmem-mcp`, and must set:

```text
STIGMEM_URL=http://localhost:8765
STIGMEM_API_KEY=<smoke-only key>
```

## Standard Steps

Run all six steps for each host included in the validated publication claim:

1. Tool discovery: all six tools appear with intact descriptions.
2. `assert_fact`: natural-language assertion creates a fact and renders cleanly.
3. `query_facts`: readback uses `query_facts`, not `recall`.
4. `recall`: content and instructions remain channel-separated; adversarial
   recalled content is not treated as privileged instruction.
5. Error display: node outage or malformed-call error is operator-readable and
   does not leak `STIGMEM_API_KEY`.
6. Session lifecycle: editor restart relaunches the MCP subprocess and fresh
   calls use fresh `mcp:<uuid>` default session identifiers.

## Per-editor Results

### Codex CLI

**Connector doc:** `experimental/mcp-adapter/connector-codex-cli.md`

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Pass | `codex mcp list` and `codex mcp get stigmem` showed the configured stdio server. A Codex host session rendered the six Stigmem MCP tools: `assert_fact`, `query_facts`, `recall`, `resolve_contradiction`, `subscribe_scope`, and `lint_scope`. |
| 2 - `assert_fact` | Pass | Codex asserted `project:codex-host-ui-smoke` / `project:codename` = `turtle-2026` with `scope=local`, `source=agent:codex`, and `session_id=codex-host-ui-smoke`. The host rendered the created fact without leaking credentials. |
| 3 - `query_facts` | Pass | Codex used `query_facts` for the exact entity/relation and returned the local `turtle-2026` fact. |
| 4 - `recall` + channel separation | Pass | Codex used `recall` for `turtle-2026`. The host result kept recalled content separate from instructions: content contained one recalled card, `instructions` was an empty array, and `system_prompt_directive` warned that Stigmem content is untrusted data and must not cross channel boundaries. |
| 5 - Error display | Pass | A malformed `assert_fact` call using `value.value` instead of required `value.v` produced a readable Zod validation error. The error did not display the MCP API key. A non-interactive `codex exec` run cancelled MCP tool calls before execution; that was recorded as host behavior, not an adapter error. |
| 6 - Session lifecycle | Pass | After the first Codex session closed, a fresh Codex session relaunched the MCP subprocess and asserted `project:codex-host-ui-smoke-reopen` / `project:session-lifecycle` = `second-session-ok` without an explicit `session_id`. `query_facts` returned exactly one matching fact with that value. |

**Editor verdict:** Pass for Codex CLI host UI smoke.

### Claude Code

**Connector doc:** `adapters/mcp/README.md`; `experimental/paperclip-adapter/concept.md`

**Host version:** Claude Code `2.1.146`

**MCP config:** temporary JSON file passed with `--mcp-config` and
`--strict-mcp-config`; no global Claude Code config was changed.

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Pass | Claude Code loaded the temporary MCP config and called Stigmem MCP tools through `adapters/mcp/dist/server.js`. The repo-local smoke also confirmed all six tools were listed before host testing. |
| 2 - `assert_fact` | Pass | Claude Code asserted `project:claude-code-host-ui-smoke` / `project:codename` = `otter-2026` with `scope=local`, `source=agent:claude-code`, `confidence=1`, and `session_id=claude-code-host-ui-smoke`. |
| 3 - `query_facts` | Pass | Claude Code used `query_facts` for the exact entity/relation and returned one fact with `value.v = "otter-2026"`. |
| 4 - `recall` + channel separation | Pass | Claude Code used `recall` for `otter-2026`; result contained one content card, an empty `instructions` array, and the untrusted-content `system_prompt_directive`. |
| 5 - Error display | Pass | A malformed `assert_fact` call using `value.value` instead of required `value.v` returned a readable Zod validation error at `["value", "v"]`. No API key, token, bearer credential, or connection string appeared in the error. |
| 6 - Session lifecycle | Pass | A fresh Claude Code session relaunched the MCP subprocess, asserted `project:claude-code-host-ui-smoke-reopen` / `project:session-lifecycle` = `second-session-ok` without an explicit `session_id`, and `query_facts` returned exactly one matching fact. |

**Editor verdict:** Pass for Claude Code host UI smoke.

### Gemini CLI

**Connector doc:** `experimental/mcp-adapter/connector-gemini-cli.md`

**Host version:** Gemini CLI `0.43.0`

**MCP config:** temporary project-scoped `.gemini/settings.json` created with
`gemini mcp add -s project --trust`, then removed after the smoke run. The
configured MCP server was verified with `gemini mcp list`.

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Pass | `gemini mcp list` reported `stigmem` connected through `node /Users/bjones/Desktop/stigmem/adapters/mcp/dist/server.js`. Repo-local smoke confirmed all six tools were listed before host testing. |
| 2 - `assert_fact` | Pass | Gemini CLI asserted `project:gemini-cli-host-ui-smoke` / `project:codename` = `maple-2026` with `scope=local`, `source=agent:gemini-cli`, `confidence=1`, and `session_id=gemini-cli-host-ui-smoke`. |
| 3 - `query_facts` | Pass | Gemini CLI queried the exact entity/relation and confirmed `value.v = "maple-2026"`. |
| 4 - `recall` + channel separation | GO-WITH-CAVEAT | Gemini CLI used `recall` for `maple-2026`; it reported separate top-level `content` and `instructions`, an empty `instructions` array, and the untrusted-content `system_prompt_directive`. The CLI also emitted `Invalid stream: The model returned an empty response or malformed tool call` after one recall/final-response render. |
| 5 - Error display | Pass | A malformed `assert_fact` call using `value.value` instead of required `value.v` returned a readable validation error at `["value", "v"]`. No API key, secret, or credential appeared in the error. |
| 6 - Session lifecycle | Pass | A fresh Gemini CLI session relaunched the MCP subprocess, asserted `project:gemini-cli-host-ui-smoke-reopen` / `project:session-lifecycle` = `second-session-ok` without an explicit `session_id`, and `query_facts` returned exactly that value. |

**Editor verdict:** GO-WITH-CAVEAT. Stigmem MCP tool calls succeeded, including
write, query, recall channel separation, malformed-call error display, and
fresh-session lifecycle. Gemini CLI `0.43.0` produced an `INVALID_STREAM`
final-response/rendering error in some runs, so package copy may mention
Gemini CLI only with this caveat until a future host version produces clean
final output.

### Continue.dev

**Connector doc:** `experimental/mcp-adapter/connector-continue-dev.md`

**Validation state:** Out of scope for `0.9.0-alpha.8` publication clearance.
The connector guide remains experimental and unvalidated until a maintainer with
Continue.dev access records real host UI results.

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Not run | Host UI unavailable for this gate. |
| 2 - `assert_fact` | Not run | Host UI unavailable for this gate. |
| 3 - `query_facts` | Not run | Host UI unavailable for this gate. |
| 4 - `recall` + channel separation | Not run | Host UI unavailable for this gate. |
| 5 - Error display | Not run | Host UI unavailable for this gate. |
| 6 - Session lifecycle | Not run | Host UI unavailable for this gate. |

**Editor verdict:** Unvalidated experimental connector; not a blocker for
Codex CLI and Claude Code alpha publication clearance.

### Cursor

**Connector doc:** `experimental/mcp-adapter/connector-cursor.md`

**Validation state:** Out of scope for `0.9.0-alpha.8` publication clearance.
The connector guide remains experimental and unvalidated until a maintainer with
Cursor access records real host UI results.

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Not run | Host UI unavailable for this gate. |
| 2 - `assert_fact` | Not run | Host UI unavailable for this gate. |
| 3 - `query_facts` | Not run | Host UI unavailable for this gate. |
| 4 - `recall` + channel separation | Not run | Host UI unavailable for this gate. |
| 5 - Error display | Not run | Host UI unavailable for this gate. |
| 6 - Session lifecycle | Not run | Host UI unavailable for this gate. |

**Editor verdict:** Unvalidated experimental connector; not a blocker for
Codex CLI and Claude Code alpha publication clearance.

### Zed

**Connector doc:** `experimental/mcp-adapter/connector-zed.md`

**Validation state:** Out of scope for `0.9.0-alpha.8` publication clearance.
The connector guide remains experimental and unvalidated until a maintainer with
Zed access records real host UI results.

| Step | Result | Notes |
| --- | --- | --- |
| 1 - Tool discovery | Not run | Host UI unavailable for this gate. |
| 2 - `assert_fact` | Not run | Host UI unavailable for this gate. |
| 3 - `query_facts` | Not run | Host UI unavailable for this gate. |
| 4 - `recall` + channel separation | Not run | Host UI unavailable for this gate. |
| 5 - Error display | Not run | Host UI unavailable for this gate. |
| 6 - Session lifecycle | Not run | Host UI unavailable for this gate. |

**Editor verdict:** Unvalidated experimental connector; not a blocker for
Codex CLI and Claude Code alpha publication clearance.

## Aggregate Go/No-go

| Editor | Verdict | Blocker for clearance? |
| --- | --- | --- |
| Codex CLI | Pass | No |
| Claude Code | Pass | No |
| Gemini CLI | GO-WITH-CAVEAT | No if package copy mentions the Gemini CLI final-response caveat; yes before claiming clean Gemini CLI host support. |
| Continue.dev | Unvalidated experimental connector | No for Codex CLI / Claude Code alpha publication and Gemini CLI caveated smoke; yes before claiming Continue support. |
| Cursor | Unvalidated experimental connector | No for Codex CLI / Claude Code alpha publication and Gemini CLI caveated smoke; yes before claiming Cursor support. |
| Zed | Unvalidated experimental connector | No for Codex CLI / Claude Code alpha publication and Gemini CLI caveated smoke; yes before claiming Zed support. |

**Overall:** GO for the Codex CLI and Claude Code MCP host UI smoke gate, with
Gemini CLI recorded as GO-WITH-CAVEAT. This does not publish `stigmem-mcp` and
does not grant maintainer publication clearance.

## Decision Rules

| Condition | Decision |
| --- | --- |
| Codex CLI and Claude Code pass all six steps and package docs clearly scope validated host support to those hosts | GO - maintainer may consider `ready-for-clearance`; this does not publish. |
| Gemini CLI passes tool execution but emits final-response/rendering errors | GO-WITH-CAVEAT only if package README and connector docs mention the limitation. |
| Any editor leaks the smoke API key | NO-GO - halt, root-cause, remediate, and re-run from Step 1. |
| Codex CLI or Claude Code fails Step 4 channel separation | NO-GO for publication; fix before clearance. |
| Codex CLI or Claude Code fails a non-Step-4 check | GO-WITH-CAVEAT only if the package README and connector doc call out the limitation. |
| Continue.dev, Cursor, or Zed remain unvalidated | Not a blocker for Codex CLI / Claude Code alpha publication or Gemini CLI caveated smoke; package and connector docs must not claim those hosts are validated. |

## Follow-up When This Gate Passes

1. Update this file with sanitized evidence, editor verdicts, and maintainer
   decision.
2. Update `docs/internal/mcp-publication-dry-run.md` to mark Codex CLI and
   Claude Code host UI smoke complete and link back here.
3. Update `docs/internal/plugin-publication-disposition.md` from `hold` to
   `ready-for-clearance` only if the maintainer wants a clearance-pending tier.
4. Keep actual npm publication as a separate maintainer-approved action.

## Scope Boundaries

- Codex CLI and Claude Code are the validated host UI smoke targets for
  `0.9.0-alpha.8`; Gemini CLI is recorded as GO-WITH-CAVEAT.
- Continue.dev, Cursor, and Zed connector guides are experimental and
  unvalidated for this publication decision.
- Tests only stdio transport.
- Does not certify production deployment.
- Does not grant publication clearance.
- Does not validate concurrent multi-editor use.
