# Engineering Log

## 2026-05-17 — Contributor and Demo Readiness

Stigmem's Phase B readiness work now has two contributor-facing demo paths:

- `make demo` runs the two-node Docker quickstart from a clean local checkout,
  registers both peers, asserts a company-scoped fact on node A, verifies
  replication on node B, prints recent federation audit entries, and tears the
  environment down.
- `make demo-attack` runs the malicious-peer rejection gate. It demonstrates
  that a public-only peer cannot push company-scoped data, and that a peer cannot
  forge the source identity on a public fact. Both cases must reject and record
  audit evidence.

Contributor onboarding was also refreshed around a small, concrete reading path:
architecture overview, single-host node, federated network, threat model, ADRs,
and `good first issue` work. The intent is that a new contributor can understand
the reference node, run the demo, pick a starter issue, and open a focused PR
without first reverse-engineering the project structure.

## Operator Soak Digest Template

Use this template for the weekly public digest once the Phase B external
operator validation soak begins:

```md
## YYYY-MM-DD — Operator Soak Digest, Week N

- Operator context: <public non-sensitive summary>
- Version under test: <commit or release tag>
- Deployment shape: <single node / same-org federation / limited federation>
- Findings opened: #NN, #NN
- Findings closed: #NN
- P0 status: none / #NN
- ADR-004 observability notes: <signals that helped or were missing>
- Next week: <planned validation focus>
```
