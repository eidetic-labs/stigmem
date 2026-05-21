# libSQL Storage Spec

## Scope

libSQL storage covers the reference node adapter selected when
`STIGMEM_STORAGE_BACKEND=libsql`. It is a child record of the storage backend
family and owns libSQL/Turso-specific behavior.

This feature covers:

- local libSQL mode with `STIGMEM_DB_PATH`;
- embedded-replica mode with `STIGMEM_DB_PATH`, `STIGMEM_LIBSQL_URL`, and
  `STIGMEM_LIBSQL_AUTH_TOKEN`;
- optional local replica encryption through the backend encryption key;
- migration execution through the libSQL client;
- row and cursor wrappers needed to satisfy the shared backend interface;
- operator recovery guidance for Turso point-in-time restore and local replica
  resync.

This feature does not own Turso service availability, Turso account policy,
cloud-region residency, or provider-side encryption controls.

## Backend Selection

The adapter is selected only when the node settings resolve
`storage_backend=libsql`. Operators must install the optional dependency group
before use:

```bash
pip install 'stigmem-node[libsql]'
```

SQLite remains the default backend. Deployments that do not explicitly select
libSQL continue to use the SQLite backend.

## Connection Modes

| Mode | Required settings | Behavior |
| --- | --- | --- |
| Local libSQL | `STIGMEM_STORAGE_BACKEND=libsql`, `STIGMEM_DB_PATH` | Opens a local database through the libSQL client. |
| Embedded replica | `STIGMEM_STORAGE_BACKEND=libsql`, `STIGMEM_DB_PATH`, `STIGMEM_LIBSQL_URL`, `STIGMEM_LIBSQL_AUTH_TOKEN` | Opens a local replica and syncs it with the configured Turso/libSQL primary on connection. |

When a sync URL is configured, the adapter calls `sync()` after connection
creation. The local replica file is treated as a cache of the remote primary.

## Migration Behavior

The adapter applies numbered SQL migrations idempotently using the
`schema_migrations` table. Because the current libSQL client does not expose
`executescript()`, migration files are split into complete SQL statements
before execution. SQLite-only FTS5 objects and trigger statements referencing
the FTS table are skipped for libSQL compatibility.

## Recovery Behavior

For remote Turso/libSQL deployments, the provider-side database is the
authoritative copy. After provider point-in-time restore, operators should
remove or move the stale local replica so the node recreates and resyncs it on
startup.

## Non-Goals

- Data migration from an existing SQLite database into Turso/libSQL.
- Provider-side backup, restore, residency, or account-security guarantees.
- Treating libSQL as part of the stable default surface.
- A wire-protocol commitment independent of the reference node adapter.

## Canonical Spec Assignment

There is no Spec-X assignment for libSQL storage. This is an implementation
adapter in the reference node, not a standalone protocol module.
