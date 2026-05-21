# Storage Backends Security

## Security Posture

Storage backends are part of the node trust boundary. SQLite default deployments
store facts locally. Non-default backends can introduce cloud, network, provider,
and data-residency dependencies.

## Threat Model Deltas

| Risk | Current mitigation |
| --- | --- |
| R-04: At-rest encryption default-off | SQLCipher and libSQL native encryption paths are available, but encryption is operator-enabled. |
| R-08: libSQL cloud backend exposure | Operators rely on TLS and Turso data residency controls; Stigmem does not add application-layer encryption for fact payloads. |
| Backend switching data loss | Operator docs require snapshots or manual migration before switching backends. |
| Local SQLite file exposure | SQLite database artifacts are restricted to owner-only permissions where supported. |
| Backend parity drift | Cross-backend conformance tests exist, but release-line certification remains ongoing. |

## Advisories and Findings

No public GHSA is currently owned by this feature record.

## Security Gaps

- R-04 remains accepted until operators enable at-rest encryption where needed.
- R-08 remains accepted for libSQL cloud deployments.
- Backend-specific rate, availability, and residency controls depend on the
  selected provider and operator configuration.
- Stable-line production guidance needs explicit backend certification evidence.
