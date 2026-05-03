#!/usr/bin/env bash
# 4-node stigmem federation soak runner.
# Usage:  cd stigmem/infra && bash soak/run_soak.sh [--hours N] [--skip-build]
# Default: 72-hour soak.  Set --hours 1 for a quick smoke-test.
#
# Requirements:
#   - Docker with Compose v2 (docker compose)
#   - Python 3.11+ with cryptography, PyJWT, requests
#     (pip install -r soak/requirements.txt)
#   - Ports 8765-8768 free on localhost
#
# Failure injections (scheduled automatically):
#   T+4h  : Partition node-c for 5 min, then reconnect (split-brain probe)
#   T+24h : Add 500ms delay to node-b for 15 min (slow-peer probe)
#   T+48h : Restart node-d container (crash-recovery probe)

set -euo pipefail

SOAK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(dirname "$SOAK_DIR")"
METRICS_DIR="$SOAK_DIR/metrics"
LOG_DIR="$SOAK_DIR/logs"
SOAK_HOURS=72
SKIP_BUILD=false

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    --hours) SOAK_HOURS="$2"; shift 2 ;;
    --skip-build) SKIP_BUILD=true; shift ;;
    *) echo "Unknown arg: $1"; exit 1 ;;
  esac
done

SOAK_DURATION_S=$(( SOAK_HOURS * 3600 ))
mkdir -p "$METRICS_DIR" "$LOG_DIR"

log() { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"; }

# ---------------------------------------------------------------------------
# Step 1: Generate keypairs (idempotent — skip if .env exists)
# ---------------------------------------------------------------------------

if [[ ! -f "$SOAK_DIR/.env" ]]; then
  log "Generating Ed25519 keypairs..."
  python3 "$SOAK_DIR/keys.py" > "$SOAK_DIR/.env"
  log "Keypairs written to soak/.env"
else
  log "soak/.env exists — reusing keypairs"
fi

# ---------------------------------------------------------------------------
# Step 2: Build and start containers
# ---------------------------------------------------------------------------

cd "$INFRA_DIR"

if [[ "$SKIP_BUILD" == "false" ]]; then
  log "Building soak images..."
  docker compose -f docker-compose.soak.yml --env-file soak/.env build --no-cache
fi

log "Starting 4-node cluster..."
docker compose -f docker-compose.soak.yml --env-file soak/.env up -d

# ---------------------------------------------------------------------------
# Step 3: Wait for all nodes healthy
# ---------------------------------------------------------------------------

log "Waiting for all nodes to be healthy..."
wait_healthy() {
  local url="$1" name="$2"
  for i in $(seq 1 60); do
    if curl -sf "$url/healthz" > /dev/null 2>&1; then
      log "  $name: healthy"
      return 0
    fi
    sleep 2
  done
  log "ERROR: $name did not become healthy within 120s"
  exit 1
}

wait_healthy http://localhost:8765 node-a
wait_healthy http://localhost:8766 node-b
wait_healthy http://localhost:8767 node-c
wait_healthy http://localhost:8768 node-d

# ---------------------------------------------------------------------------
# Step 4: Register full-mesh peers
# ---------------------------------------------------------------------------

log "Registering full-mesh peers..."
python3 "$SOAK_DIR/setup_peers.py" --env "$SOAK_DIR/.env"

# ---------------------------------------------------------------------------
# Step 5: Start seed and metrics in background
# ---------------------------------------------------------------------------

log "Starting seed loop..."
python3 "$SOAK_DIR/seed.py" > "$LOG_DIR/seed.log" 2>&1 &
SEED_PID=$!
log "  seed PID: $SEED_PID"

log "Starting metrics collector..."
python3 "$SOAK_DIR/metrics_collector.py" > "$LOG_DIR/metrics.log" 2>&1 &
METRICS_PID=$!
log "  metrics PID: $METRICS_PID"

# ---------------------------------------------------------------------------
# Step 6: Schedule failure injections
# ---------------------------------------------------------------------------

schedule_failure() {
  local delay_s="$1" name="$2" fn="$3"
  (sleep "$delay_s" && log "=== Failure injection: $name ===" && eval "$fn") &
}

# T+4h: Partition node-c for 5 minutes
schedule_failure $((4 * 3600)) "partition-node-c-5min" '
  docker network disconnect soak_net soak-node-c
  log "  node-c disconnected from soak_net"
  sleep 300
  docker network connect soak_net soak-node-c
  log "  node-c reconnected to soak_net"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),partition_node_c,5min" >> '"$METRICS_DIR"'/failure_events.csv
'

# T+24h: Add 500ms delay to node-b for 15 minutes
schedule_failure $((24 * 3600)) "slow-peer-node-b-15min" '
  docker exec soak-node-b sh -c "apt-get install -yq iproute2 2>/dev/null; tc qdisc add dev eth0 root netem delay 500ms 50ms distribution normal" || true
  log "  node-b: added 500ms network delay"
  sleep 900
  docker exec soak-node-b tc qdisc del dev eth0 root 2>/dev/null || true
  log "  node-b: network delay removed"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),slow_peer_node_b,15min" >> '"$METRICS_DIR"'/failure_events.csv
'

# T+48h: Restart node-d (crash recovery)
schedule_failure $((48 * 3600)) "restart-node-d" '
  docker restart soak-node-d
  log "  node-d: restarted (cursor resume test)"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ),restart_node_d,instant" >> '"$METRICS_DIR"'/failure_events.csv
'

# ---------------------------------------------------------------------------
# Cleanup trap
# ---------------------------------------------------------------------------

cleanup() {
  log "Soak stopping — sending SIGTERM to background processes..."
  kill "$SEED_PID" "$METRICS_PID" 2>/dev/null || true
  wait "$SEED_PID" "$METRICS_PID" 2>/dev/null || true
  log "Metrics files in $METRICS_DIR:"
  ls -lh "$METRICS_DIR"/*.csv 2>/dev/null || true
  log "To stop containers:  docker compose -f docker-compose.soak.yml down"
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Step 7: Run for configured duration
# ---------------------------------------------------------------------------

START_TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
log "=== Soak started at $START_TS (${SOAK_HOURS}h) ==="
log "Monitor: tail -f $LOG_DIR/metrics.log"
log "Conflicts: curl http://localhost:8765/v1/conflicts | python3 -m json.tool"

sleep "$SOAK_DURATION_S"

END_TS=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
log "=== Soak completed at $END_TS ==="
log "Review metrics in $METRICS_DIR then populate stigmem/docs/soak-report-4node.md"
