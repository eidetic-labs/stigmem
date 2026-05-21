# Storage Backends Spec

## Scope

Storage backends define the node persistence boundary. The node uses a common
backend interface for connection lifecycle, transaction semantics, migration
application, and optional snapshot hooks.

This feature covers:

- default SQLite persistence;
- the shared `StorageBackend` interface;
- backend selection through node settings;
- migration application through the configured backend;
- backend-specific conformance and encryption evidence;
- operator guidance for choosing SQLite, libSQL/Turso, or Postgres.

This feature does not own the detailed behavior of any external storage service.
Cloud provider security, availability, and data residency remain operator and
provider responsibilities.

## Backend Contract

Every backend must provide:

| Capability | Requirement |
| --- | --- |
| Connection lifecycle | Yield a SQLite-API-compatible connection object. |
| Transactions | Commit on clean exit and roll back on exception. |
| Row access | Support column lookup by name. |
| Migrations | Apply numbered SQL migrations idempotently. |
| Snapshot hooks | Implement or explicitly reject export/import snapshot operations. |

## Backend Selection

The node selects a backend from settings. SQLite is the default. Non-default
backends are opt-in and require their own environment settings and package
extras.

Common operator choices:

| Backend | Use when |
| --- | --- |
| SQLite | Single-host, local development, air-gapped, or sovereign deployments. |
| libSQL/Turso | Hosted deployments that need cloud-backed durability or embedded replicas. |
| Postgres | Operators already running managed Postgres and pgvector. |

## Migration Contract

Migrations must be idempotent. Already-applied versions are tracked in
`schema_migrations` and skipped on later runs. Plugin-declared migrations run
after core migrations through the plugin migration registry.

## Canonical Spec Assignment

There is no Spec-X assignment for storage backends. This is an implementation
adapter boundary in the reference node rather than a standalone wire protocol
module.
