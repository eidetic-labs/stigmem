# libSQL Storage Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/storage/libsql_backend.py` | libSQL/Turso backend implementation, connection wrapper, migration splitter, and encryption-key forwarding. |
| `node/src/stigmem_node/storage/__init__.py` | Backend factory branch for `storage_backend=libsql`. |
| `node/src/stigmem_node/settings.py` | `STIGMEM_STORAGE_BACKEND`, `STIGMEM_LIBSQL_URL`, and `STIGMEM_LIBSQL_AUTH_TOKEN` settings. |
| `node/src/stigmem_node/db.py` | Backend selection and migration application entry points. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `node/tests/storage/test_encryption.py` | libSQL encrypted local mode where `libsql-experimental` is installed. |
| `node/tests/utility/test_immutability_l1.py` | SQL migration splitter behavior for trigger bodies. |
| `node/src/stigmem_conformance/tests/` | Backend-parameterized conformance suite; libSQL cases skip when the optional dependency is absent. |
| `node/tests/conftest.py` | Test fixture support for the `--backend=libsql` path. |

## Operator Docs

| Path | Coverage |
| --- | --- |
| `experimental/storage-libsql/concept.md` | Turso point-in-time restore and local replica recovery guidance. |
| `docs/docs/operators/conformance.md` | Backend conformance expectations and libSQL test invocation. |
| `docs/docs/operators/runbooks/deploy-runbooks.md` | Deployment setting examples for libSQL-backed operation. |
| `docs/docs/security/encryption-at-rest.md` | Local encryption guidance including the libSQL optional dependency path. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- End-to-end Turso restore evidence is not yet release-certified.
- Backend parity evidence is incomplete for all node routes.
- Data migration from existing SQLite files into libSQL/Turso is not provided.
