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
| ADR | Feature-owned plugin record and source-of-truth structure. | Complete | ADR-020. |
| Conformance vectors | Forgery, non-admin issuance, legal hold, revocation, federation authority, and no-leak checks. | Complete for `v0.9.0a5` alpha scope | `node/tests/tombstones/`; `node/tests/time_travel/`; plugin tests. |
| Operator soak | Regulated-data workflow soak. | Open | None currently recorded. |
| Documentation parity | Feature record, security projection, and release-note projection. | Partial | Feature-owned docs are current; operator runbooks remain open. |

## Known Gaps

- Signed/package artifact evidence is deferred until the plugin artifact is
  published.
- Two-admin approval, dedicated legal-hold roles, operator soak, and
  revocation runbooks need design before graduation.
