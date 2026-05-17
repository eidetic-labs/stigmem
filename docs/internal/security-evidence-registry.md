# Security Evidence Registry — Best Practices

> A risk is not `Mitigated` because the design says it should be. It is `Mitigated` when implementation evidence, test evidence, version-introduced evidence, and operational documentation all agree.

## Required Artifact

Maintain a machine-readable evidence file, for example:

```yaml
risks:
  R-01:
    title: mTLS federation peer authentication
    status: mitigated
    version_introduced: 0.9.0a1
    implementation:
      - node/src/stigmem_node/tls.py
      - node/src/stigmem_node/main.py
    tests:
      - node/tests/federation/test_mtls.py
    docs:
      - docs/security/mtls.md
      - spec/security/threat-model.md
    review_record: docs/internal/security-evidence/R-01.md
```

The exact path can vary, but the structure must be regular enough for a script to validate.

## Status Rules

- `Open`: no accepted mitigation.
- `In review`: implementation exists but evidence review is incomplete.
- `Mitigated`: implementation, tests, docs, and version-introduced are recorded.
- `Residual`: mitigation exists but known residual risk remains.
- `Accepted`: risk deliberately retained with rationale and owner.

## CI Validation

Add a script that verifies:

- every `Mitigated` risk has at least one implementation file
- every listed implementation file exists
- every listed test file exists
- every listed docs file exists
- `version_introduced` matches the release/version vocabulary
- every threat-model `Mitigated` risk appears in the evidence registry

The script should not decide whether evidence is good. It prevents evidence from being missing, stale, or path-broken.

## Review Record Template

Each control review record should answer:

- What code was inspected?
- What tests prove the behavior?
- What negative tests prove failure modes?
- What version introduced the control?
- What docs tell operators how to use or verify it?
- Decision: accept as-is, patch, or replace.
- Reviewer names and date.

## Current Stigmem Use

Stigmem now keeps the machine-readable registry at
`spec/security/evidence-registry.json`. CI runs
`scripts/validate_security_evidence.py` whenever the threat model, registry,
colocated feature-security docs, contributor guidance, or validator changes.

The cross-phase owner/trigger map for this control lives in
`docs/internal/evidence-maintenance.md`.
