#!/usr/bin/env bash
# stigmem/adapters/mcp/tests/smoke.sh
#
# MCP server smoke test — exercises the full JSON-RPC protocol end-to-end:
#   initialize → tools/list → assert_fact → query_facts → recall → lint_scope
#
# Usage:
#   cd stigmem          (or any directory — script resolves paths relative to itself)
#   bash stigmem/adapters/mcp/tests/smoke.sh
#
# Environment overrides:
#   STIGMEM_URL        Base URL of a live node (default: http://localhost:8765)
#   STIGMEM_API_KEY    API key (optional; omit for unauthenticated nodes)
#   STIGMEM_SESSION_ID Session id propagated by the adapter (default: generated smoke id)
#   KEEP_SERVER        Set to 1 to leave the server process running after the test

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MCP_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_JS="$MCP_DIR/dist/server.js"

STIGMEM_URL="${STIGMEM_URL:-http://localhost:8765}"
STIGMEM_SESSION_ID="${STIGMEM_SESSION_ID:-mcp:smoke-$(date +%s)-$$}"
KEEP_SERVER="${KEEP_SERVER:-0}"
SERVER_PID=""
REQ_FIFO=""
RESP_FIFO=""

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "  ✓ $*"; }
fail() { echo "  ✗ $*" >&2; exit 1; }

cleanup() {
  exec 3>&- 2>/dev/null || true   # close write end
  exec 4<&- 2>/dev/null || true   # close read end
  if [[ -n "$SERVER_PID" && "$KEEP_SERVER" != "1" ]]; then
    kill "$SERVER_PID" 2>/dev/null || true
  fi
  [[ -n "$REQ_FIFO" ]]  && rm -f "$REQ_FIFO"
  [[ -n "$RESP_FIFO" ]] && rm -f "$RESP_FIFO"
}
trap cleanup EXIT

# ---- step 0: build check -------------------------------------------------------

log "Step 0 — Checking MCP server build"
if [[ ! -f "$SERVER_JS" ]]; then
  log "  dist/server.js not found; running pnpm build…"
  (cd "$MCP_DIR" && pnpm install --silent && pnpm build --silent)
fi
ok "dist/server.js present"

# ---- step 1: start server ------------------------------------------------------

log "Step 1 — Starting MCP server"

REQ_FIFO=$(mktemp -t stigmem-mcp-req.XXXXXX)
RESP_FIFO=$(mktemp -t stigmem-mcp-resp.XXXXXX)
rm "$REQ_FIFO" "$RESP_FIFO"
mkfifo "$REQ_FIFO" "$RESP_FIFO"

ENV_VARS=("STIGMEM_URL=$STIGMEM_URL" "STIGMEM_SESSION_ID=$STIGMEM_SESSION_ID")
if [[ -n "${STIGMEM_API_KEY:-}" ]]; then
  ENV_VARS+=("STIGMEM_API_KEY=$STIGMEM_API_KEY")
fi

env "${ENV_VARS[@]}" node "$SERVER_JS" <"$REQ_FIFO" >"$RESP_FIFO" 2>/dev/null &
SERVER_PID=$!

# Open write end so the server doesn't get EOF immediately
exec 3>"$REQ_FIFO"

# Open read end once and keep it open — re-opening loses buffered data
exec 4<"$RESP_FIFO"

ok "MCP server started (pid $SERVER_PID)"

# ---- helpers -------------------------------------------------------------------

send_msg() {
  # Write a JSON-RPC NDJSON message to the server's stdin (fd 3).
  printf '%s\n' "$1" >&3
}

read_response() {
  # Read one newline-delimited JSON line from the server's stdout (fd 4).
  local line
  if ! IFS= read -r -t 8 line <&4 2>/dev/null; then
    fail "Timed out waiting for MCP response"
  fi
  echo "$line"
}

extract_text_payload() {
  python3 -c "
import sys, json
d = json.load(sys.stdin)
content = d.get('result', {}).get('content', [])
assert content, f'empty content: {d}'
print(content[0]['text'])
"
}

# ---- step 2: initialize --------------------------------------------------------

log "Step 2 — MCP initialize handshake"

INIT_MSG='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"stigmem-smoke-test","version":"0.0.1"}}}'
send_msg "$INIT_MSG"
INIT_RESP=$(read_response)

echo "$INIT_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('id') == 1, f'expected id=1, got {d}'
assert 'result' in d, f'no result key: {d}'
assert 'serverInfo' in d['result'], f'no serverInfo: {d}'
" || fail "initialize response invalid: $INIT_RESP"

# Send initialized notification (no response expected)
send_msg '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}'
ok "Handshake complete (server: $(echo "$INIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['result']['serverInfo']['name']+' '+d['result']['serverInfo']['version'])"))"

# ---- step 3: tools/list --------------------------------------------------------

log "Step 3 — tools/list"
send_msg '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
TOOLS_RESP=$(read_response)

TOOLS_SUMMARY=$(echo "$TOOLS_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('id') == 2, f'expected id=2'
tools = {t['name'] for t in d['result']['tools']}
expected = {'assert_fact', 'query_facts', 'recall', 'resolve_contradiction', 'subscribe_scope', 'lint_scope'}
missing = expected - tools
assert not missing, f'missing tools: {missing}'
print(f'found {len(tools)} tools: {sorted(tools)}')
" 2>&1) || fail "tools/list check failed: $TOOLS_SUMMARY"

ok "$TOOLS_SUMMARY"

# ---- step 4: assert_fact -------------------------------------------------------

log "Step 4 — tools/call assert_fact (write a smoke-test fact)"

RUN_ID="$(date +%s)-$$"
SMOKE_ENTITY="stigmem://smoke-test/fact/zed-e2e-$RUN_ID"
SMOKE_SOURCE="stigmem://smoke-test/agent/smoke-test"
ASSERT_CALL=$(python3 -c "
import json
msg = {
  'jsonrpc': '2.0',
  'id': 3,
  'method': 'tools/call',
  'params': {
    'name': 'assert_fact',
    'arguments': {
      'entity': '$SMOKE_ENTITY',
      'relation': 'smoke:status',
      'value': {'type': 'string', 'v': 'zed-smoke-ok'},
      'source': '$SMOKE_SOURCE',
      'confidence': 1.0,
      'scope': 'local',
      'session_id': '$STIGMEM_SESSION_ID'
    }
  }
}
print(json.dumps(msg))
")
send_msg "$ASSERT_CALL"
ASSERT_RESP=$(read_response)

ASSERT_SUMMARY=$(echo "$ASSERT_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('id') == 3, f'expected id=3'
assert 'result' in d, f'no result: {d}'
content = d['result'].get('content', [])
assert content, f'empty content'
fact = json.loads(content[0]['text'])
assert fact.get('id'), f'no fact id in: {fact}'
print(f'fact id={fact[\"id\"]} entity={fact[\"entity\"]}')
" 2>&1) || fail "assert_fact failed: $ASSERT_SUMMARY. Response: $ASSERT_RESP"

ok "$ASSERT_SUMMARY"

# ---- step 5: query_facts -------------------------------------------------------

log "Step 5 — tools/call query_facts (read back the asserted fact)"

QUERY_CALL=$(python3 -c "
import json
print(json.dumps({
  'jsonrpc': '2.0',
  'id': 4,
  'method': 'tools/call',
  'params': {
    'name': 'query_facts',
    'arguments': {
      'entity': '$SMOKE_ENTITY',
      'relation': 'smoke:status',
      'scope': 'local',
      'limit': 1,
      'session_id': '$STIGMEM_SESSION_ID'
    }
  }
}))
")
send_msg "$QUERY_CALL"
QUERY_RESP=$(read_response)

QUERY_SUMMARY=$(echo "$QUERY_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('id') == 4, f'expected id=4'
assert 'result' in d, f'no result: {d}'
content = d['result'].get('content', [])
assert content, f'empty content'
page = json.loads(content[0]['text'])
facts = page.get('facts', [])
assert facts, f'no facts returned: {page}'
v = facts[0].get('value', {}).get('v', '')
assert v == 'zed-smoke-ok', f'unexpected value: {v}'
print(f'retrieved {len(facts)} fact(s); value.v={v}')
" 2>&1) || fail "query_facts check failed: $QUERY_SUMMARY. Response: $QUERY_RESP"

ok "$QUERY_SUMMARY"

# ---- step 6: recall -----------------------------------------------------------

log "Step 6 — tools/call recall (retrieve the asserted fact through recall)"

RECALL_CALL=$(python3 -c "
import json
print(json.dumps({
  'jsonrpc': '2.0',
  'id': 5,
  'method': 'tools/call',
  'params': {
    'name': 'recall',
    'arguments': {
      'query': 'zed-smoke-ok smoke:status',
      'scope': 'local',
      'token_budget': 1000,
      'depth': 1,
      'include_neighbors': False,
      'limit': 5,
      'session_id': '$STIGMEM_SESSION_ID'
    }
  }
}))
")
send_msg "$RECALL_CALL"
RECALL_RESP=$(read_response)

RECALL_SUMMARY=$(echo "$RECALL_RESP" | extract_text_payload | python3 -c "
import sys, json
payload = json.load(sys.stdin)
assert 'system_prompt_directive' in payload, f'missing directive: {payload}'
assert isinstance(payload.get('content'), list), f'missing content channel: {payload}'
assert isinstance(payload.get('instructions'), list), f'missing instructions channel: {payload}'
content_text = json.dumps(payload.get('content', []))
assert 'zed-smoke-ok' in content_text, f'smoke fact not recalled: {payload}'
print(f'recall returned {len(payload.get(\"content\", []))} content fact(s) and {len(payload.get(\"instructions\", []))} instruction fact(s)')
" 2>&1) || fail "recall check failed: $RECALL_SUMMARY. Response: $RECALL_RESP"

ok "$RECALL_SUMMARY"

# ---- step 7: lint_scope -------------------------------------------------------

log "Step 7 — tools/call lint_scope (read-only live lint sweep)"

LINT_CALL=$(python3 -c "
import json
print(json.dumps({
  'jsonrpc': '2.0',
  'id': 6,
  'method': 'tools/call',
  'params': {
    'name': 'lint_scope',
    'arguments': {
      'scope': 'local',
      'checks': ['stale', 'broken_ref'],
      'entity': '$SMOKE_ENTITY'
    }
  }
}))
")
send_msg "$LINT_CALL"
LINT_RESP=$(read_response)

LINT_SUMMARY=$(echo "$LINT_RESP" | extract_text_payload | python3 -c "
import sys, json
payload = json.load(sys.stdin)
assert payload.get('scope') == 'local', f'unexpected scope: {payload}'
assert 'findings' in payload, f'missing findings: {payload}'
assert 'checked_at' in payload, f'missing checked_at: {payload}'
checks = set(payload.get('checks_run', []))
expected = {'stale', 'broken_ref'}
assert expected.issubset(checks), f'checks not run: {payload}'
print(f'lint checked {payload.get(\"fact_count\")} fact(s); findings={len(payload.get(\"findings\", []))}')
" 2>&1) || fail "lint_scope check failed: $LINT_SUMMARY. Response: $LINT_RESP"

ok "$LINT_SUMMARY"

# ---- summary -------------------------------------------------------------------

echo ""
echo "========================================"
echo " Stigmem MCP smoke test PASSED"
echo "========================================"
echo ""
echo "Verified:"
echo "  • MCP initialize handshake"
echo "  • tools/list returns all 6 Stigmem tools"
echo "  • tools/call assert_fact writes a fact to the node"
echo "  • tools/call query_facts retrieves the asserted fact"
echo "  • tools/call recall returns channel-separated recalled content"
echo "  • tools/call lint_scope completes a read-only node sweep"
echo "  • STIGMEM_SESSION_ID is supplied to session-aware tool calls"
echo ""
echo "Node URL: $STIGMEM_URL"
echo "Session ID: $STIGMEM_SESSION_ID"
