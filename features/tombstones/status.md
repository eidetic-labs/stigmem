# RTBF Tombstones Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `opt-in` |

Tombstone source exists on `main` as an experimental plugin package. Default
installs do not expose tombstone behavior unless `stigmem-plugin-tombstones` is
registered.

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | R-16 and R-17 ownership. | Open | `features/tombstones/security.md` |
| ADR | Reintroduction design. | Open | Deferred. |
| Conformance vectors | Forgery, non-admin issuance, legal hold, revocation, federation authority. | Partial | `node/tests/tombstones/`; plugin tests. |
| Operator soak | Regulated-data workflow soak. | Open | None currently recorded. |
| Documentation parity | Operator runbooks and API docs. | Open | Artifact publication deferred. |

## Known Gaps

- Signed/package artifact evidence is deferred to the plugin launch lane.
- Two-admin approval, dedicated legal-hold roles, and revocation runbooks need
  design before graduation.
- Federation propagation semantics need additional adversarial coverage.
