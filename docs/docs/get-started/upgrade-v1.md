---
title: Pre-v0.9.0a1 Upgrade Notes
sidebar_label: Pre-v0.9.0a1 notes
---

# Pre-v0.9.0a1 Upgrade Notes

**Audience:** Operators with an older local checkout, stale dependency pin, or
pre-reset deployment artifact who need to align with the `v0.9.0a1` alpha reset.

No `v1.0` or `v2.0` Stigmem release shipped publicly. Per ADR-001 and
ADR-019, `v0.9.0a1` is the first build. Treat older `v0.x`, `v1.x`, and `v2.0`
labels in local branches, old docs, or unpublished artifacts as internal
development checkpoints.

For source checkouts, the alignment path is still a `git pull` plus rebuild.
The node applies migrations at startup; take a database backup first if your
local data matters.

## What changed in the alpha reset

### Multi-tenant isolation (migration `012`)

The storage schema includes `tenant_id` columns on write-bearing tables for
compatibility with the extracted multi-tenant plugin. On upgrade:

- All existing rows receive `tenant_id = "default"` automatically.
- Existing API keys continue to work in the `"default"` tenant.
- Single-tenant deployments require zero configuration changes.
- Default installs collapse tenant resolution to `"default"` unless the
  opt-in multi-tenant plugin is registered.

See [Multi-Tenancy](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) for the extracted plugin source package.

### Billing hooks

A new `stigmem_node.billing` module emits a `BillingEvent` after every fact write and garden creation. The default implementation logs structured JSON to stderr — no configuration needed unless you want a custom backend. See [Billing Hooks](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/billing).

### Source attestation

Source attestation remains experimental in the v0.9.0aN line (`Spec-X6-Source-Attestation`). Default installs keep source-attestation behavior off; runtime enforcement is moving behind `stigmem-plugin-source-attestation` registration and explicit plugin configuration. See [Source Attestation](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/source-attestation).

### Conformance test suite

The source tree includes conformance and adversarial suites that drive the
current alpha/beta readiness gates. The public compatibility contract remains
pre-GA; pin exact versions and do not assume wire-format stability until the
roadmap reaches `v1.0.0`.

---

## Upgrade procedure

### Docker Compose (recommended)

```bash
git pull
docker compose up --build -d
```

The node runs `apply_migrations()` on startup. Migration `012_multi_tenant` is
idempotent; if it has already run in an older local checkout, it is skipped.

Verify the node is healthy and the migration applied:

```bash
curl -s http://localhost:8765/healthz
# → {"status": "ok"}

sqlite3 data/stigmem.db "SELECT version FROM schema_migrations ORDER BY version;"
# Should include: 012_multi_tenant
```

### Without Docker (development install)

```bash
git pull
uv sync          # or: pip install -e .
python -m stigmem_node
```

### Persistent service (macOS LaunchAgent)

```bash
git pull
uv sync
launchctl kickstart -k gui/$(id -u)/com.eidetic-labs.stigmem
```

---

## Verifying existing data after alignment

Facts and gardens from older local checkouts live in `tenant_id = "default"`.
Confirm with any of your existing API keys:

```bash
# Your existing key still works, now in tenant "default"
curl -s -H 'Authorization: Bearer <existing-key>' \
  http://localhost:8765/v1/me
# → {"entity_uri": "...", "permissions": [...], "tenant_id": "default"}

# Facts are still accessible
curl -s -H 'Authorization: Bearer <existing-key>' \
  'http://localhost:8765/v1/facts?limit=5' | jq '.[].id'
```

---

## Breaking changes

The alpha reset is not a stable-release upgrade path. The supported public
surface is `v0.9.0a1` plus current `main` changes queued for later alpha
artifacts. Breaking changes may occur until `v1.0.0`.

The only behavior difference is billing events: the `LogHookBus` now writes a JSON line to stderr for each fact write and garden creation. If your log ingestion pipeline is sensitive to unexpected stderr output, either configure a custom `HookBus` that discards events or filter the `{"billing": ...}` lines at your log collector.

---

## Migration history at a glance

| Migration | What it adds | Required for current source? |
|-----------|--------------|---------------------|
| `001_init` | facts, api_keys, node_meta | ✓ (baseline) |
| `002_federation` | peers, nonces | required for federation |
| `006_agent_keys` | Ed25519 agent key registration | required for source attestation |
| `007_fact_audit` | end-to-end audit log | required for audit queries |
| `011_facts_garden_attested` | `garden_id` + `attested` columns | ✓ |
| `012_multi_tenant` | `tenant_id` on all write-bearing tables | ✓ |

All migrations run automatically at startup in ascending numeric order. There is no rollback mechanism — take a database backup before upgrading if your data is critical.

---

## See also

- [Installation](./installation) — fresh install with Docker Compose
- [Multi-Tenancy](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/multi-tenant) — tenant isolation model
- [Billing Hooks](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/billing) — hooking into write events
- [Source Attestation](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/source-attestation) — hardening entity_uri binding
- [Audit Log](../security/audit-log) — querying the per-principal write trail
