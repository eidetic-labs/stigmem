# systemd Deploy Recipe

Bare-metal or air-gapped Linux host, no Docker required.
Tested on Debian 12, Ubuntu 22.04 LTS, RHEL 9, Fedora 40.

## Prerequisites

- Python 3.11+ (`python3 --version`)
- systemd
- Root access (`sudo`)

## Install

```bash
# From repo root:
sudo bash deploy/systemd/install.sh
```

The installer:
1. Creates a `stigmem` system user (no login shell)
2. Creates `/opt/stigmem/` (install) and `/var/lib/stigmem/` (data)
3. Creates a Python venv at `/opt/stigmem/venv/` and installs `stigmem-node`
4. Copies `.env.example` → `/opt/stigmem/.env` (mode 600, only if not present)
5. Installs and enables `stigmem-node.service`

## Configure and start

```bash
# 1. Edit the env file
sudo nano /opt/stigmem/.env
#    At minimum, set STIGMEM_NODE_URL to the node's public URL.

# 2. Start and verify
sudo systemctl start stigmem-node
sudo systemctl status stigmem-node
curl http://localhost:8765/healthz

# 3. Smoke-test write + read
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{"entity":"node","relation":"status","value":{"type":"string","v":"up"},"source":"smoke","scope":"local"}'

curl -s 'http://localhost:8765/v1/facts?entity=node&scope=local' | python3 -m json.tool
```

## Logs

```bash
sudo journalctl -u stigmem-node -f
sudo journalctl -u stigmem-node --since "1 hour ago"
```

## Upgrade

```bash
sudo -u stigmem /opt/stigmem/venv/bin/pip install --upgrade \
  "stigmem-node==<NEW_VERSION>"
sudo systemctl restart stigmem-node
```

## Reverse proxy (recommended)

Bind the node to `127.0.0.1` (default) and put Caddy or nginx in front:

**Caddy** (`/etc/caddy/Caddyfile`):
```
stigmem.example.com {
    reverse_proxy 127.0.0.1:8765
}
```

**nginx** (`/etc/nginx/sites-available/stigmem`):
```nginx
server {
    listen 443 ssl;
    server_name stigmem.example.com;
    # ... TLS config ...
    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Update `STIGMEM_NODE_URL` in `.env` to the public HTTPS URL after configuring TLS.

## Air-gapped / offline install

```bash
# On a connected machine, download wheels:
pip3 download --pre "stigmem-node==0.9.0a1" -d wheels/

# Copy wheels/ to the target, then:
STIGMEM_OFFLINE=1 WHEEL_DIR=/path/to/wheels \
  sudo bash deploy/systemd/install.sh
```

## Uninstall

```bash
sudo systemctl stop stigmem-node
sudo systemctl disable stigmem-node
sudo rm /etc/systemd/system/stigmem-node.service
sudo systemctl daemon-reload
sudo rm -rf /opt/stigmem
# Data is preserved at /var/lib/stigmem — remove manually if no longer needed.
```
