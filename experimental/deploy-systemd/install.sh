#!/usr/bin/env bash
# install.sh — Bare-metal stigmem node installer for Debian/Ubuntu and RHEL/Fedora.
#
# Usage (run as root or with sudo):
#   sudo bash experimental/deploy-systemd/install.sh
#
# After install:
#   1. Edit /opt/stigmem/.env (copied from .env.example)
#   2. sudo systemctl start stigmem
#   3. sudo journalctl -u stigmem -f
#
# Requirements: Python 3.11+, curl or pip3 available.
# Air-gapped installs: run `pip3 download stigmem-node -d wheels/` on a connected
# machine, copy the wheels/ directory here, then set STIGMEM_OFFLINE=1.

set -euo pipefail

INSTALL_DIR=/opt/stigmem
DATA_DIR=/var/lib/stigmem
SERVICE_FILE=/etc/systemd/system/stigmem-node.service
STIGMEM_USER=stigmem
STIGMEM_GROUP=stigmem
PYTHON_MIN_VERSION="3.11"
STIGMEM_VERSION="${STIGMEM_VERSION:-0.9.0a2}"
STIGMEM_OFFLINE="${STIGMEM_OFFLINE:-0}"

# ── Helpers ───────────────────────────────────────────────────────────────────
info()  { echo "[stigmem-install] $*"; }
error() { echo "[stigmem-install] ERROR: $*" >&2; exit 1; }

require_root() {
  [[ $EUID -eq 0 ]] || error "Run as root or with sudo"
}

check_python() {
  local python_bin
  python_bin=$(command -v python3 2>/dev/null) || error "python3 not found; install Python $PYTHON_MIN_VERSION+"
  local ver
  ver=$("$python_bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  python3 -c "import sys; assert sys.version_info >= (3,11)" \
    || error "Python $ver found; Python $PYTHON_MIN_VERSION+ is required"
  info "Python $ver OK"
}

# ── Main ──────────────────────────────────────────────────────────────────────
require_root
check_python

info "Creating system user $STIGMEM_USER"
if ! id "$STIGMEM_USER" &>/dev/null; then
  useradd --system --no-create-home --shell /sbin/nologin \
          --home-dir "$INSTALL_DIR" "$STIGMEM_USER"
fi

info "Creating directories"
mkdir -p "$INSTALL_DIR" "$DATA_DIR"
chown "$STIGMEM_USER:$STIGMEM_GROUP" "$DATA_DIR"
chmod 750 "$DATA_DIR"

info "Creating Python virtual environment"
python3 -m venv "$INSTALL_DIR/venv"

info "Installing stigmem-node"
if [[ "$STIGMEM_OFFLINE" == "1" ]]; then
  WHEEL_DIR="${WHEEL_DIR:-$(dirname "$0")/wheels}"
  [[ -d "$WHEEL_DIR" ]] || error "STIGMEM_OFFLINE=1 but WHEEL_DIR=$WHEEL_DIR does not exist"
  "$INSTALL_DIR/venv/bin/pip" install --no-index --find-links "$WHEEL_DIR" \
    "stigmem-node==$STIGMEM_VERSION"
else
  "$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
  "$INSTALL_DIR/venv/bin/pip" install --quiet "stigmem-node==$STIGMEM_VERSION"
fi

info "Copying environment template"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
  cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/.env"
  chown "$STIGMEM_USER:$STIGMEM_GROUP" "$INSTALL_DIR/.env"
  chmod 600 "$INSTALL_DIR/.env"
  info "Created $INSTALL_DIR/.env — EDIT THIS FILE before starting the service"
else
  info "$INSTALL_DIR/.env already exists; leaving it unchanged"
fi

info "Installing systemd unit"
cp "$SCRIPT_DIR/stigmem-node.service" "$SERVICE_FILE"
systemctl daemon-reload
systemctl enable stigmem-node

info ""
info "Installation complete."
info ""
info "Next steps:"
info "  1. Edit /opt/stigmem/.env  (set STIGMEM_NODE_URL and any secrets)"
info "  2. sudo systemctl start stigmem-node"
info "  3. sudo systemctl status stigmem-node"
info "  4. curl http://localhost:8765/healthz"
info ""
info "Logs: sudo journalctl -u stigmem-node -f"
