# Source Attestation Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `opt-in` |

Source-attestation source exists on `main` as an experimental plugin package.
Default installs remain inert; operators must register the plugin and enable
the relevant `STIGMEM_SOURCE_ATTESTATION_*` gates before enforcement or ranking
behavior runs.

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Threat-model delta | R-22 contribution and source-binding boundary. | Open | `features/source-attestation/security.md` |
| ADR | Reintroduction design. | Open | Deferred. |
| Conformance vectors | Enforce/warn/off, delegation, rotation, federation. | Partial | Plugin scaffold and validation tests, including normalized assertion-source and delegated-source checks. |
| Operator soak | External validation. | Open | None currently recorded. |
| Documentation parity | Operator docs and artifact evidence. | Open | Artifact publication deferred. |

## Known Gaps

- Signed/package artifact evidence is deferred to the all-plugins launch lane.
- Key-rotation, API-backed delegation persistence, and federation-source evidence
  must expand before graduation.
- Release signing and SBOM/Rekor provenance remain owned by R-22, not by this
  feature alone.
