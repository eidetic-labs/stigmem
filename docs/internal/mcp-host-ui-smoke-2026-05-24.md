# MCP Host UI Smoke — 2026-05-24

**Status:** not yet executed; Codex CLI is the only required host UI clearance
gate for `0.9.0-alpha.8`
**Operator:** pending
**stigmem-mcp version:** `0.9.0-alpha.8` at commit pending
**stigmem-node version:** `0.9.0a8` at commit pending
**Date:** 2026-05-24
**Node URL:** `http://localhost:8765` loopback
**API key label:** `mcp-host-ui-smoke-2026-05-24` smoke-only key

This record is the PR-attachable execution artifact for the MCP adapter host UI
smoke gate. It complements the repo-local stdio smoke in
`adapters/mcp/tests/smoke.sh`; it does not replace that automated protocol
coverage.

`0.9.0-alpha.8` narrows the publication clearance claim to Codex CLI plus the
repo-local MCP protocol smoke. Continue.dev, Cursor, and Zed connector guides
remain experimental and unvalidated because those host UIs are not available in
the maintainer environment for this gate. Do not describe those three hosts as
validated in package or release material until a future PR records real host UI
results.

Do not move `stigmem-mcp` from `hold` to a publication-ready disposition until
this file records a real Codex CLI PASS, GO-WITH-CAVEAT, or explicit maintainer
NO-GO decision. Maintainer publication clearance remains a separate action.

## Pre-flight

Run once before testing any editor:

```bash
cd ~/Desktop/stigmem
uv run stigmem-node --listen 127.0.0.1:8765 --log-level info
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8765/health
```

Generate or register a smoke-only API key for the local node. Do not use a
production key. If the local node accepts arbitrary test-key registration, use
the recognizable sentinel value `stk_smoke_NEVER_LEAK_THIS_2026-05-24` so any
accidental log exposure is obvious.

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

Run all six steps for Codex CLI:

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
| 1 - Tool discovery | Pending | Paste rendered tool names and descriptions. |
| 2 - `assert_fact` | Pending | Paste sanitized tool-call/result snippet. |
| 3 - `query_facts` | Pending | Confirm query result includes the Step 2 fact. |
| 4 - `recall` + channel separation | Pending | Critical F-S2 gate; record adversarial-content result. |
| 5 - Error display | Pending | Confirm no smoke API key appears in exported logs. |
| 6 - Session lifecycle | Pending | Record pre/post restart `session_id` values. |

**Editor verdict:** Pending

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
Codex-only alpha publication clearance.

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
Codex-only alpha publication clearance.

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
Codex-only alpha publication clearance.

## Aggregate Go/No-go

| Editor | Verdict | Blocker for clearance? |
| --- | --- | --- |
| Codex CLI | Pending | Yes |
| Continue.dev | Unvalidated experimental connector | No for Codex-only alpha publication; yes before claiming Continue support. |
| Cursor | Unvalidated experimental connector | No for Codex-only alpha publication; yes before claiming Cursor support. |
| Zed | Unvalidated experimental connector | No for Codex-only alpha publication; yes before claiming Zed support. |

**Overall:** NO-GO until Codex CLI host UI smoke results are recorded.

## Decision Rules

| Condition | Decision |
| --- | --- |
| Codex CLI passes all six steps and package docs clearly scope validated host support to Codex CLI | GO - maintainer may consider `ready-for-clearance`; this does not publish. |
| Any editor leaks the smoke API key | NO-GO - halt, root-cause, remediate, and re-run from Step 1. |
| Codex CLI fails Step 4 channel separation | NO-GO for publication; fix before clearance. |
| Codex CLI fails a non-Step-4 check | GO-WITH-CAVEAT only if the package README and connector doc call out the limitation. |
| Continue.dev, Cursor, or Zed remain unvalidated | Not a blocker for Codex-only alpha publication; package and connector docs must not claim those hosts are validated. |

## Follow-up When This Gate Passes

1. Update this file with sanitized evidence, editor verdicts, and maintainer
   decision.
2. Update `docs/internal/mcp-publication-dry-run.md` to mark Codex CLI host UI
   smoke complete and link back here.
3. Update `docs/internal/plugin-publication-disposition.md` from `hold` to
   `ready-for-clearance` only if the maintainer wants a clearance-pending tier.
4. Keep actual npm publication as a separate maintainer-approved action.

## Scope Boundaries

- Codex CLI is the only required host UI smoke target for `0.9.0-alpha.8`.
- Continue.dev, Cursor, and Zed connector guides are experimental and
  unvalidated for this publication decision.
- Tests only stdio transport.
- Does not certify production deployment.
- Does not grant publication clearance.
- Does not validate concurrent multi-editor use.
