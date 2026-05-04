# Deploy Recipes

Pick the recipe that matches your environment:

```
Are you using a managed PaaS?
  ├── Fly.io (recommended for small teams)  →  deploy/fly/
  ├── Render / Railway / App Runner / Cloud Run  →  deploy/paas/
  └── Kubernetes / enterprise self-hosted  →  deploy/helm/

Are you running on your own Linux host?
  ├── Docker available?  →  deploy/compose/
  └── No Docker (bare metal / air-gapped / sovereign)  →  deploy/systemd/
```

## Quick comparison

| Recipe | Best for | Persistence | HA |
|---|---|---|---|
| [Fly.io](./fly/) | Personal / small team; zero-config TLS | Fly volume or Turso (libSQL) | Multi-region via Fly machines |
| [Compose](./compose/) | Local dev / single-server self-host | Docker volume or bind-mount | No (single process) |
| [Helm](./helm/) | Kubernetes / enterprise | PVC (any StorageClass) | Multiple replicas + ingress |
| [systemd](./systemd/) | Sovereign, air-gapped, bare metal | Local filesystem | No (single process) |
| [PaaS](./paas/) | Fastest start on hosted cloud | Platform-provided or Turso | Depends on platform |

## Common environment variables

All recipes share the same `STIGMEM_*` env var space.
See [node/src/stigmem_node/settings.py](../node/src/stigmem_node/settings.py) for the full list.

Key variables every operator should review:

| Variable | Default | Notes |
|---|---|---|
| `STIGMEM_NODE_URL` | `http://localhost:8765` | Public URL of this node; included in federation handshakes |
| `STIGMEM_AUTH_REQUIRED` | `false` | Set `true` in production |
| `STIGMEM_FEDERATION_ENABLED` | `false` | Enable when peering with other nodes |
| `STIGMEM_STORAGE_BACKEND` | `sqlite` | `sqlite` or `libsql` |
| `STIGMEM_AT_REST_ENCRYPTION` | `off` | Set `on` + supply key for encrypted DB |
| `STIGMEM_LOG_LEVEL` | `info` | `debug` / `info` / `warning` / `error` |

## No secrets in these files

All secret values (keys, tokens, passwords) are shown as `<PLACEHOLDER>`.
Set them via your platform's secrets manager or an env file that is **not** committed to git.
