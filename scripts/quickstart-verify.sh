#!/usr/bin/env bash
# quickstart-verify.sh — end-to-end smoke test for the stigmem two-node quickstart.
#
# Runs the full quickstart sequence from scratch:
#   1. Build + start two nodes via Docker Compose
#   2. Wait for both nodes to be healthy
#   3. Inspect /.well-known/stigmem on each
#   4. Register node-a as a peer on node-b
#   5. Assert a fact on node-a
#   6. Wait for the pull loop and verify the fact appears on node-b
#   7. Tear down
#
# Usage:
#   cd stigmem
#   bash scripts/quickstart-verify.sh
#
# Environment overrides:
#   PULL_WAIT_S   Seconds to wait for federation pull (default: 35)
#   KEEP_UP       Set to 1 to skip teardown (useful for debugging)

set -euo pipefail

PULL_WAIT_S="${PULL_WAIT_S:-35}"
KEEP_UP="${KEEP_UP:-0}"
START_TIME=$(date +%s)

# ---- helpers -----------------------------------------------------------------

log()  { echo "[$(date '+%H:%M:%S')] $*"; }
ok()   { echo "  ✓ $*"; }
fail() { echo "  ✗ $*" >&2; exit 1; }

# Returns 0 if the given TCP port is bound by ANY process, 1 if free.
# Uses lsof (macOS/Linux); falls back to a /dev/tcp probe if lsof unavailable.
port_in_use() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN
    else
        # /dev/tcp probe as a fallback (bash builtin; no extra deps)
        (echo > /dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
    fi
}

# Find the next free TCP port at-or-above $1, capped at $1+200 to avoid runaway.
find_free_port() {
    local port="$1" cap=$(( $1 + 200 ))
    while [[ "$port" -le "$cap" ]]; do
        if ! port_in_use "$port"; then
            echo "$port"
            return 0
        fi
        port=$(( port + 1 ))
    done
    fail "no free TCP port found in range $1..$cap"
}

wait_healthy() {
    local url="$1" label="$2" retries=30 i
    log "Waiting for $label to be healthy…"
    for (( i=0; i<retries; i++ )); do
        if curl -sf "$url/healthz" >/dev/null 2>&1; then
            ok "$label is healthy"
            return 0
        fi
        sleep 2
    done
    fail "$label did not become healthy after $((retries * 2)) s"
}

# ---- port selection ----------------------------------------------------------
#
# Smoke test picks two free host ports starting from 18765. Any process
# bound to a candidate port (other stigmem-node instances, Paperclip-managed
# servers, dev tunnels, unrelated services) gets skipped automatically. The
# canonical adopter UX in docker-compose.yml is still 8765/8766; override
# explicitly via STIGMEM_NODE_A_HOST_PORT / STIGMEM_NODE_B_HOST_PORT in env
# if you want to test the canonical port mapping (and accept the collision
# risk).

if [[ -n "${STIGMEM_NODE_A_HOST_PORT:-}" && -n "${STIGMEM_NODE_B_HOST_PORT:-}" ]]; then
    log "Using explicit host ports from env: A=${STIGMEM_NODE_A_HOST_PORT} B=${STIGMEM_NODE_B_HOST_PORT}"
    if port_in_use "${STIGMEM_NODE_A_HOST_PORT}"; then
        fail "STIGMEM_NODE_A_HOST_PORT=${STIGMEM_NODE_A_HOST_PORT} is in use"
    fi
    if port_in_use "${STIGMEM_NODE_B_HOST_PORT}"; then
        fail "STIGMEM_NODE_B_HOST_PORT=${STIGMEM_NODE_B_HOST_PORT} is in use"
    fi
else
    NODE_A_PORT=$(find_free_port 18765)
    NODE_B_PORT=$(find_free_port $(( NODE_A_PORT + 1 )))
    export STIGMEM_NODE_A_HOST_PORT="$NODE_A_PORT"
    export STIGMEM_NODE_B_HOST_PORT="$NODE_B_PORT"
    log "Auto-selected free host ports: node-a=$NODE_A_PORT  node-b=$NODE_B_PORT"
fi
NODE_A="http://localhost:${STIGMEM_NODE_A_HOST_PORT}"
NODE_B="http://localhost:${STIGMEM_NODE_B_HOST_PORT}"

# ---- pre-flight: clear stale state -------------------------------------------
#
# Belt-and-suspenders teardown of any previous run that exited dirty (KEEP_UP=1
# left up; SIGINT during run; previous failure before the teardown step).
# Removes the volumes too — peer registrations and ingested facts live in
# /data/stigmem.db inside the volume, so leaving them around would cause
# "peer already registered (409)" responses on the next run's handshake.

log "Pre-flight: clearing any stale containers + volumes from a prior run…"
docker compose down -v --remove-orphans 2>&1 | tail -3 || true

# ---- step 0: build + start ---------------------------------------------------

log "Step 0 — docker compose up --build -d"
docker compose up --build -d
ok "Containers started"

# ---- step 1: health ----------------------------------------------------------

wait_healthy "$NODE_A" "node-a"
wait_healthy "$NODE_B" "node-b"

# ---- step 2: well-known ------------------------------------------------------

log "Step 2 — Inspecting /.well-known/stigmem"
NODE_A_ID=$(curl -sf "$NODE_A/.well-known/stigmem" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['node_id'])")
NODE_B_ID=$(curl -sf "$NODE_B/.well-known/stigmem" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['node_id'])")
ok "node-a node_id: $NODE_A_ID"
ok "node-b node_id: $NODE_B_ID"

[[ -n "$NODE_A_ID" ]] || fail "node-a node_id is empty"
[[ -n "$NODE_B_ID" ]] || fail "node-b node_id is empty"
[[ "$NODE_A_ID" != "$NODE_B_ID" ]] || fail "node-a and node-b share the same node_id"

# ---- step 3: federation handshake (both directions) -------------------------

log "Step 3 — Peer handshake (both directions)"
CONTAINER_A=$(docker compose ps --format '{{.Name}}' | grep node-a | head -1)
CONTAINER_B=$(docker compose ps --format '{{.Name}}' | grep node-b | head -1)
[[ -n "$CONTAINER_A" ]] || fail "Could not find node-a container"
[[ -n "$CONTAINER_B" ]] || fail "Could not find node-b container"
ok "node-a container: $CONTAINER_A"
ok "node-b container: $CONTAINER_B"

log "  Registering node-a with node-b…"
docker exec "$CONTAINER_A" \
    stigmem federation register-peer \
        --local-url  http://node-a:8765 \
        --remote-url http://node-b:8765 \
        --scopes company,public

log "  Registering node-b with node-a…"
docker exec "$CONTAINER_B" \
    stigmem federation register-peer \
        --local-url  http://node-b:8765 \
        --remote-url http://node-a:8765 \
        --scopes company,public

# ---- step 4: assert fact on node-a ------------------------------------------

log "Step 4 — Asserting fact on node-a"
ENTITY="user:quickstart-smoke-$(date +%s)"
FACT_RESP=$(curl -sf -X POST "$NODE_A/v1/facts" \
    -H 'Content-Type: application/json' \
    -d "{
        \"entity\":     \"$ENTITY\",
        \"relation\":   \"memory:prefers\",
        \"value\":      {\"type\":\"string\",\"v\":\"dark mode\"},
        \"source\":     \"agent:smoke-test\",
        \"confidence\": 1.0,
        \"scope\":      \"company\"
    }")
FACT_ID=$(echo "$FACT_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
ok "Fact asserted on node-a (id=$FACT_ID, entity=$ENTITY)"

# ---- step 5: wait + verify replication on node-b ----------------------------

log "Step 5 — Waiting ${PULL_WAIT_S}s for federation pull…"
sleep "$PULL_WAIT_S"

log "Querying node-b for replicated fact…"
FACTS_ON_B=$(curl -sf "$NODE_B/v1/facts?entity=$ENTITY&scope=company" \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('facts',[]))) ")

if [[ "$FACTS_ON_B" -ge 1 ]]; then
    ok "Fact replicated to node-b ($FACTS_ON_B result(s))"
else
    fail "Fact NOT found on node-b after ${PULL_WAIT_S}s (entity=$ENTITY)"
fi

# ---- step 6: audit log -------------------------------------------------------

log "Step 6 — Federation audit log on node-b (last 3 entries)"
curl -sf "$NODE_B/v1/federation/audit" \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
entries = d.get('entries', [])[-3:]
for e in entries:
    print(f\"  {e.get('event','?')}  peer={e.get('peer_id','?')[:8]}…  at={e.get('created_at','?')[:19]}\")
"

# ---- summary -----------------------------------------------------------------

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))
echo ""
echo "========================================"
echo " quickstart smoke test PASSED (${ELAPSED}s)"
echo "========================================"

# ---- teardown ----------------------------------------------------------------

if [[ "$KEEP_UP" != "1" ]]; then
    log "Tearing down…"
    docker compose down -v --remove-orphans
    ok "Cleaned up"
fi
