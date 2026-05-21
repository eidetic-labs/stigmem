# Storage Backends Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/storage/base.py` | Shared `StorageBackend` interface. |
| `node/src/stigmem_node/storage/sqlite_backend.py` | Default SQLite backend and SQLCipher/sqlite-vec integration hooks. |
| `node/src/stigmem_node/storage/libsql_backend.py` | libSQL/Turso backend implementation. |
| `node/src/stigmem_node/storage/postgres_backend.py` | Postgres backend implementation and SQL compatibility wrapper. |
| `node/src/stigmem_node/db.py` | Backend selection, migration application, and plugin migration integration. |
| `node/src/stigmem_node/settings.py` | Backend-selection and backend-specific settings. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `node/tests/storage/test_sqlite_permissions.py` | SQLite database artifact permission hardening. |
| `node/tests/storage/test_encryption.py` | SQLite SQLCipher and libSQL encryption paths where dependencies are installed. |
| `node/tests/storage/test_postgres_backend.py` | Postgres backend SQL compatibility and backend behavior. |
| `node/src/stigmem_conformance/tests/` | Cross-backend behavioral conformance suite. |

## Operator Docs

| Path | Coverage |
| --- | --- |
| `experimental/storage-backends/concept-choose.md` | Backend decision tree and switching guidance. |
| `experimental/storage-backends/concept-index.md` | Backend overview and operator setup material. |
| `docs/docs/operators/conformance.md` | Backend conformance expectations. |
| `docs/docs/operators/runbooks/backup-restore.md` | Backup and restore expectations for local and cloud backends. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- Release-line backend certification evidence is not complete.
- Backend migration and data-copy runbooks need explicit end-to-end validation.
- Cloud-provider-specific restore and data residency evidence is operator-owned.
