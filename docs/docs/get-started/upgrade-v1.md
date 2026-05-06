---
title: Upgrading to v1.0
sidebar_label: Upgrading to v1.0
---

# Upgrading to v1.0

**Audience:** Operators running a stigmem node on any v0.x release who want to upgrade to the stable v1.0 reference node.

v1.0 is backward compatible with all v0.x data. The upgrade is a `git pull` + container rebuild. No manual SQL or data migration is required.

## What changed in v1.0

### Multi-tenant isolation (migration `012`)

v1.0 adds `tenant_id` columns to `facts`, `gardens`, `api_keys`, and `fact_audit_log`. On upgrade:

- All existing rows receive `tenant_id = "default"` automatically.
- All existing API keys continue to work and operate in the `"default"` tenant.
- Single-tenant deployments require zero configuration changes.

See [Multi-Tenancy](../../security/multi-tenancy) for the full model.

### Billing hooks

A new `stigmem_node.billing` module emits a `BillingEvent` after every fact write and garden creation. The default implementation logs structured JSON to stderr — no configuration needed unless you want a custom backend. See [Billing Hooks](../../build/guides/billing-hooks).

### Source attestation (v1.0 normative)

Source attestation was experimental in v0.9-draft. In v1.0 it is normative (§18). The default mode is unchanged (`warn`), so existing deployments are unaffected. To harden a production node, set `STIGMEM_SOURCE_ATTESTATION_MODE=enforce`. See [Source Attestation](../../build/guides/source-attestation).

### Conformance test suite

v1.0 ships a conformance suite (`node/tests/conformance/`) that any compliant node implementation can run. CI enforces it on every commit.

---

## Upgrade procedure

### Docker Compose (recommended)

```bash
git pull
docker compose up --build -d
```

The node runs `apply_migrations()` on startup. Migration `012_multi_tenant` is idempotent — if it has already run (e.g., on a v0.9-rc build) it is skipped.

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

## Verifying existing data after upgrade

All pre-v1.0 facts and gardens live in `tenant_id = "default"`. Confirm with any of your existing API keys:

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

## Adding a second tenant (optional)

After upgrading you can start issuing keys for additional tenants. Existing data in `"default"` is unaffected:

```bash
curl -s -X POST http://localhost:8765/v1/auth/keys \
  -H 'Authorization: Bearer <admin-key>' \
  -H 'Content-Type: application/json' \
  -d '{
    "entity_uri": "service:beta-app",
    "permissions": ["read", "write"],
    "tenant_id": "beta-inc"
  }'
```

Keys issued for `beta-inc` see only facts written by `beta-inc` keys. See [Multi-Tenancy → Isolation in practice](../../security/multi-tenancy#isolation-in-practice) for a cross-tenant verification example.

---

## Breaking changes

None. v1.0 is fully backward compatible with v0.x data and API keys.

The only behavior difference is billing events: the `LogHookBus` now writes a JSON line to stderr for each fact write and garden creation. If your log ingestion pipeline is sensitive to unexpected stderr output, either configure a custom `HookBus` that discards events or filter the `{"billing": ...}` lines at your log collector.

---

## Migration history at a glance

| Migration | What it adds | Mandatory for v1.0? |
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
- [Multi-Tenancy](../../security/multi-tenancy) — tenant isolation model
- [Billing Hooks](../../build/guides/billing-hooks) — hooking into write events
- [Source Attestation](../../build/guides/source-attestation) — hardening entity_uri binding
- [Audit Log](../../build/guides/audit-log) — querying the per-principal write trail
