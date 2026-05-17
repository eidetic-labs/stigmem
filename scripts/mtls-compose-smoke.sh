#!/usr/bin/env bash
# End-to-end smoke test for the two-node mTLS compose federation example.

set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-stigmem-mtls-smoke}"
COMPOSE_FILE="${COMPOSE_FILE:-deploy/compose/docker-compose.mtls.yml}"
TLS_DIR_CREATED="0"
if [[ -z "${TLS_DIR:-}" ]]; then
    mkdir -p "${HOME}/.stigmem"
    TLS_DIR="$(mktemp -d "${HOME}/.stigmem/mtls-compose-smoke-tls.XXXXXX")"
    TLS_DIR_CREATED="1"
fi
export STIGMEM_MTLS_TLS_DIR="$TLS_DIR"
PULL_WAIT_S="${PULL_WAIT_S:-35}"
KEEP_UP="${KEEP_UP:-0}"
START_TIME="$(date +%s)"

log() { echo "[$(date '+%H:%M:%S')] $*"; }
ok() { echo "  ✓ $*"; }
fail() { echo "  ✗ $*" >&2; exit 1; }

port_in_use() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | grep -q LISTEN
    else
        (echo > /dev/tcp/127.0.0.1/"$port") >/dev/null 2>&1
    fi
}

find_free_port() {
    local port="$1"
    local cap=$(($1 + 200))
    while [[ "$port" -le "$cap" ]]; do
        if ! port_in_use "$port"; then
            echo "$port"
            return 0
        fi
        port=$((port + 1))
    done
    fail "no free TCP port found in range $1..$cap"
}

compose() {
    docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" "$@"
}

cleanup() {
    if [[ "$KEEP_UP" == "1" ]]; then
        log "KEEP_UP=1; leaving compose project $PROJECT_NAME running"
        return
    fi
    log "Tearing down compose project $PROJECT_NAME..."
    compose down -v --remove-orphans >/dev/null 2>&1 || true
    if [[ "$TLS_DIR_CREATED" == "1" ]]; then
        rm -rf "$TLS_DIR"
    fi
}
trap cleanup EXIT

wait_healthy() {
    local name="$1" port="$2" cert="$3" key="$4" retries=30 i
    log "Waiting for $name to pass HTTPS mTLS health..."
    for ((i = 0; i < retries; i++)); do
        if curl -fsS \
            --noproxy '*' \
            --resolve "$name:$port:127.0.0.1" \
            --cacert "$TLS_DIR/ca.crt" \
            --cert "$cert" \
            --key "$key" \
            "https://$name:$port/healthz" >/dev/null 2>&1; then
            ok "$name is healthy over mTLS"
            return 0
        fi
        sleep 2
    done
    fail "$name did not become healthy over mTLS after $((retries * 2))s"
}

json_count_facts() {
    python3 -c "import sys,json; print(len(json.load(sys.stdin).get('facts', [])))"
}

if [[ -z "${STIGMEM_MTLS_NODE_A_HOST_PORT:-}" || -z "${STIGMEM_MTLS_NODE_B_HOST_PORT:-}" ]]; then
    export STIGMEM_MTLS_NODE_A_HOST_PORT="$(find_free_port 18765)"
    export STIGMEM_MTLS_NODE_B_HOST_PORT="$(find_free_port "$((STIGMEM_MTLS_NODE_A_HOST_PORT + 1))")"
fi
export STIGMEM_FEDERATION_PULL_INTERVAL_S="${STIGMEM_FEDERATION_PULL_INTERVAL_S:-5}"

log "Using host ports: node-a=$STIGMEM_MTLS_NODE_A_HOST_PORT node-b=$STIGMEM_MTLS_NODE_B_HOST_PORT"
log "Generating local-only mTLS demo certificates..."
./deploy/compose/generate-mtls-demo-certs.sh "$TLS_DIR" >/dev/null 2>&1
ok "Certificate material generated under $TLS_DIR"

log "Pre-flight cleanup for compose project $PROJECT_NAME..."
compose down -v --remove-orphans >/dev/null 2>&1 || true

log "Starting mTLS compose stack without STIGMEM_FEDERATION_INSECURE..."
compose up --build -d
ok "Compose stack started"

wait_healthy "stigmem-a" "$STIGMEM_MTLS_NODE_A_HOST_PORT" "$TLS_DIR/node-a.crt" "$TLS_DIR/node-a.key"
wait_healthy "stigmem-b" "$STIGMEM_MTLS_NODE_B_HOST_PORT" "$TLS_DIR/node-b.crt" "$TLS_DIR/node-b.key"

CONTAINER_A="$(compose ps --format '{{.Name}}' stigmem-a | head -1)"
CONTAINER_B="$(compose ps --format '{{.Name}}' stigmem-b | head -1)"
[[ -n "$CONTAINER_A" ]] || fail "could not find stigmem-a container"
[[ -n "$CONTAINER_B" ]] || fail "could not find stigmem-b container"
ok "Found containers: $CONTAINER_A, $CONTAINER_B"

log "Registering federation peers over HTTPS with client certificates..."
docker exec "$CONTAINER_A" \
    stigmem federation register-peer \
        --local-url https://stigmem-a:8765 \
        --remote-url https://stigmem-b:8765 \
        --scopes company,public \
        --tls-cert /tls/node-a.crt \
        --tls-key /tls/node-a.key \
        --ca-bundle /tls/ca.crt

docker exec "$CONTAINER_B" \
    stigmem federation register-peer \
        --local-url https://stigmem-b:8765 \
        --remote-url https://stigmem-a:8765 \
        --scopes company,public \
        --tls-cert /tls/node-b.crt \
        --tls-key /tls/node-b.key \
        --ca-bundle /tls/ca.crt
ok "Peers registered"

ENTITY="stigmem://compose/smoke/$(date +%s)"
log "Asserting public-scope fact on node-a..."
FACT_ID="$(
    curl -fsS -X POST \
        --noproxy '*' \
        --resolve "stigmem-a:$STIGMEM_MTLS_NODE_A_HOST_PORT:127.0.0.1" \
        --cacert "$TLS_DIR/ca.crt" \
        --cert "$TLS_DIR/node-a.crt" \
        --key "$TLS_DIR/node-a.key" \
        "https://stigmem-a:$STIGMEM_MTLS_NODE_A_HOST_PORT/v1/facts" \
        -H 'Content-Type: application/json' \
        -d "{
            \"entity\":\"$ENTITY\",
            \"relation\":\"compose:mtls-smoke\",
            \"value\":{\"type\":\"string\",\"v\":\"ok\"},
            \"source\":\"stigmem://compose/node-a\",
            \"confidence\":1.0,
            \"scope\":\"public\"
        }" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])"
)"
ok "Fact asserted on node-a: $FACT_ID"

log "Waiting ${PULL_WAIT_S}s for federation pull..."
sleep "$PULL_WAIT_S"

log "Checking replicated fact on node-b..."
FACTS_ON_B="$(
    curl -fsS \
        --noproxy '*' \
        --resolve "stigmem-b:$STIGMEM_MTLS_NODE_B_HOST_PORT:127.0.0.1" \
        --cacert "$TLS_DIR/ca.crt" \
        --cert "$TLS_DIR/node-b.crt" \
        --key "$TLS_DIR/node-b.key" \
        "https://stigmem-b:$STIGMEM_MTLS_NODE_B_HOST_PORT/v1/facts?entity=$ENTITY&scope=public" \
        | json_count_facts
)"

if [[ "$FACTS_ON_B" -lt 1 ]]; then
    fail "replicated fact not found on node-b after ${PULL_WAIT_S}s"
fi
ok "Fact replicated to node-b"

ELAPSED="$(($(date +%s) - START_TIME))"
echo ""
echo "mTLS compose smoke test PASSED (${ELAPSED}s)"
