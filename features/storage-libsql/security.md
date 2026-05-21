# libSQL Storage Security

## Threat Model Delta

libSQL storage adds a third-party storage provider and a local embedded-replica
file to the storage trust boundary. Operators who enable the adapter must treat
Turso/libSQL credentials, remote database access, and local replica files as
deployment-sensitive assets.

## Mitigations

| Risk | Mitigation | Evidence |
| --- | --- | --- |
| `R-04` | Local replica encryption is supported when an encryption key and compatible libSQL client are available. | `node/src/stigmem_node/storage/libsql_backend.py`; `node/tests/storage/test_encryption.py` |
| `R-08` | The adapter keeps libSQL opt-in and requires explicit backend settings plus optional dependency installation. | `node/src/stigmem_node/storage/libsql_backend.py`; `node/src/stigmem_node/settings.py` |

## Residual Risk

- Remote Turso/libSQL deployments depend on provider availability, account
  controls, transport security, retention windows, and data residency choices.
- `STIGMEM_LIBSQL_AUTH_TOKEN` is a secret and must be stored through the
  deployment secret manager, not committed to source.
- The local replica can become stale after provider-side restore and must be
  removed or moved before restart so it resyncs from the authoritative remote
  database.
- libSQL remains outside the default surface; production use requires operator
  acceptance of third-party storage risk.

## Advisories and Findings

None currently recorded for the libSQL adapter. Related storage-family risks
are indexed by [`features/storage-backends/security.md`](../storage-backends/security.md).
