# libSQL Storage Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `opt-in` |

The libSQL adapter exists in source and can be selected by configuration, but it
remains experimental. Release-line readiness depends on backend parity,
dependency availability, restore validation, and operator runbook evidence.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | libSQL/Turso adapter work existed in the alpha-era node and was tracked as deferred experimental storage surface area. | `experimental/storage-libsql/STATUS.md`; `node/src/stigmem_node/storage/libsql_backend.py` |
| `0.9.xA` planned | Continue adapter parity, restore, and encryption validation before promoting operational guidance. | `ROADMAP.md`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Backend adapter | Implement the shared storage backend contract for libSQL/Turso. | Partial | `node/src/stigmem_node/storage/libsql_backend.py` |
| Optional dependency | Keep libSQL as an explicit optional install surface. | Partial | `node/src/stigmem_node/storage/libsql_backend.py`; `CHANGELOG.md` |
| Migration compatibility | Run core migrations through the libSQL client. | Partial | `node/src/stigmem_node/storage/libsql_backend.py`; `node/tests/utility/test_immutability_l1.py` |
| Encryption path | Support encrypted local replica files when dependency support is available. | Partial | `node/tests/storage/test_encryption.py` |
| Restore guidance | Document Turso point-in-time restore and local replica recovery. | Partial | `experimental/storage-libsql/concept.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- Backend switching does not copy existing SQLite data into Turso/libSQL.
- Full release-line certification is not complete.
- Restore guidance depends on Turso plan capabilities and should be validated
  against the supported deployment profile before release promotion.
- FTS5-specific migration objects are skipped because the current libSQL client
  path does not support them.
