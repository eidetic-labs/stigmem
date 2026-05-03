#!/usr/bin/env bash
# Installs and starts stigmem as a macOS LaunchAgent (user-level, no sudo required).
# Auto-restarts on crash; starts automatically on login.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VENV_BIN="$PROJECT_DIR/.venv/bin/stigmem-node"
DB_PATH="$PROJECT_DIR/data/stigmem.db"
LOG_DIR="$PROJECT_DIR/logs"
PLIST_LABEL="com.eidetic-labs.stigmem"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCH_AGENTS_DIR/$PLIST_LABEL.plist"

if [[ ! -f "$VENV_BIN" ]]; then
  echo "Error: stigmem-node not found at $VENV_BIN" >&2
  echo "Run 'uv sync' in $PROJECT_DIR first." >&2
  exit 1
fi

mkdir -p "$PROJECT_DIR/data" "$LOG_DIR" "$LAUNCH_AGENTS_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${PLIST_LABEL}</string>

  <key>ProgramArguments</key>
  <array>
    <string>${VENV_BIN}</string>
  </array>

  <key>WorkingDirectory</key>
  <string>${PROJECT_DIR}</string>

  <key>EnvironmentVariables</key>
  <dict>
    <key>STIGMEM_HOST</key>
    <string>127.0.0.1</string>
    <key>STIGMEM_PORT</key>
    <string>8765</string>
    <key>STIGMEM_DB_PATH</key>
    <string>${DB_PATH}</string>
    <key>STIGMEM_NODE_URL</key>
    <string>http://localhost:8765</string>
    <key>STIGMEM_FEDERATION_ENABLED</key>
    <string>false</string>
    <key>STIGMEM_LOG_LEVEL</key>
    <string>info</string>
  </dict>

  <key>KeepAlive</key>
  <true/>

  <key>RunAtLoad</key>
  <true/>

  <key>StandardOutPath</key>
  <string>${LOG_DIR}/stigmem.log</string>

  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/stigmem-error.log</string>
</dict>
</plist>
PLIST

# Reload if already registered, otherwise bootstrap fresh
GUI_DOMAIN="gui/$(id -u)"
if launchctl print "${GUI_DOMAIN}/${PLIST_LABEL}" &>/dev/null; then
  echo "Reloading existing stigmem service..."
  launchctl bootout "${GUI_DOMAIN}" "$PLIST_PATH" 2>/dev/null || true
  sleep 1
fi
launchctl bootstrap "${GUI_DOMAIN}" "$PLIST_PATH"

echo ""
echo "stigmem service installed."
echo "  DB:        $DB_PATH"
echo "  Stdout:    $LOG_DIR/stigmem.log"
echo "  Stderr:    $LOG_DIR/stigmem-error.log"
echo "  Plist:     $PLIST_PATH"
echo ""
echo "Waiting for service to start..."
for i in $(seq 1 10); do
  if curl -sf http://127.0.0.1:8765/healthz &>/dev/null; then
    echo "  Health: OK (http://127.0.0.1:8765/healthz)"
    echo ""
    echo "Verify:    lsof -i :8765"
    exit 0
  fi
  sleep 1
done
echo "  Health: not yet reachable — check logs at $LOG_DIR/stigmem-error.log"
exit 1
