# Spec-X6-Source-Attestation — Status

source-attestation is Extracted / opt-in experimental on `main`; owner core maintainers; buildable as source package for validation; last updated 2026-05-17. Spec ID: `Spec-X6-Source-Attestation`. Legacy section: Spec-X6-Source-Attestation.

This feature remains outside the default surface per [ADR-002](../../docs/adr/002-v1-scope.md) and [ADR-009](../../docs/adr/009-repo-structure.md); shared promotion gates live in [../STATUS-GATES.md](../STATUS-GATES.md).

Gate 1 threat-model delta is tracked in [`security.md`](security.md). It records
source attestation's R-22 contribution and keeps release supply-chain integrity
canonical in the protocol-level threat model.

The source package now provides `stigmem-plugin-source-attestation` metadata,
configuration gates, and hook handlers for assertion validation, recall ranking,
and federation inbound validation. Default installs remain inert: source
attestation does not run unless the plugin is registered and the relevant
`STIGMEM_SOURCE_ATTESTATION_*` gates are explicitly enabled.

Signed/package artifact launch, publication, and release evidence remain deferred
to the all-plugins launch lane. This status records source availability and
validation on `main`, not a released installable plugin artifact.
