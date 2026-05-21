# Storage Backends Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `opt-in` |

SQLite remains the default storage path. The storage backend abstraction and
non-default backends are active in source but experimental for operators until
backend parity, durability, and operational runbooks are fully certified.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Storage backend work existed in the alpha-era node and was tracked as deferred experimental surface area. | `experimental/storage-backends/STATUS.md`; `node/src/stigmem_node/storage/` |
| `0.9.xA` planned | Continue backend parity, conformance, and operator runbook validation. | `ROADMAP.md`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Backend trait | Provide a shared connection, transaction, migration, and snapshot interface. | Partial | `node/src/stigmem_node/storage/base.py` |
| SQLite default | Preserve the default SQLite behavior and permissions hardening. | Partial | `node/src/stigmem_node/storage/sqlite_backend.py`; `node/tests/storage/test_sqlite_permissions.py` |
| Non-default backend parity | Validate libSQL and Postgres behavior against conformance tests. | Partial | `node/src/stigmem_conformance/tests/`; `node/tests/storage/` |
| Operator guidance | Document backend selection, switching, and recovery expectations. | Partial | `experimental/storage-backends/`; `docs/docs/operators/` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- Backend switching does not copy existing data.
- Non-default backend operator runbooks still need release-line certification.
- libSQL cloud data residency and transport posture remain accepted risks.
- Postgres remains an opt-in backend and needs ongoing parity evidence.
