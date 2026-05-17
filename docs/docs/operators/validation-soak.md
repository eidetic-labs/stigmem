---
title: Operator Validation Soak
sidebar_label: Operator Validation Soak
description: How external operators run the Phase B validation soak and report findings.
audience: Operator
---

# Operator Validation Soak

The Phase B operator validation soak is the public evidence gate before
Stigmem can declare the `v1.0.0rcN` line. At least one external operator must
run the hardened core for 30 days, report findings publicly when safe, and
confirm that P0 findings are fixed or explicitly carried forward.

This page is the shared checklist for operators and maintainers.

## What the operator runs

The validation target is the supported hardened-core surface:

- reference node deployment using the current `main` branch or the release tag
  named by maintainers;
- local or same-organization federation using documented peer setup;
- mTLS, key rotation, audit log, observability, and runbook surfaces exercised
  where they apply to the operator's deployment;
- no unsupported experimental plugin behavior unless the issue explicitly says
  the operator is validating that plugin as a separate ADR-008 gate.

Cross-organization production federation remains pre-stable until the soak
finishes and the project declares the release-candidate line.

## Before the soak starts

Maintainers and the operator should agree on:

| Item | Evidence |
|---|---|
| Deployment shape | Public operator-candidate issue with non-sensitive context |
| Version under test | Commit SHA or release tag |
| Topology | Single node, same-org federation, or limited cross-org test |
| Reporting path | Public issues for non-sensitive findings; private advisory path for vulnerabilities |
| Weekly cadence | LOG.md digest entry or GitHub Discussion link |
| Stop conditions | P0 finding, secret exposure, unsafe deployment pattern, or operator request |

Do not put secrets, private topology diagrams, private customer data, exploit
details, or unpublished vulnerability details in public issues.

## Weekly digest

Each week, maintainers should add a short digest to `LOG.md` or link a public
Discussion. Use this shape:

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

## Finding triage

Open public findings with the **Operator finding** issue template whenever the
report can be shared safely. Maintainers apply:

- `type/operator-finding` for all soak findings;
- `operator-soak-finding` for findings produced during the 30-day soak;
- `severity/P0` when the finding blocks safe continuation.

P0 findings stop the soak until the operator and maintainers agree it is safe to
continue. Fix PRs should reference the finding issue and include the validation
that proves the fix.

## ADR-004 feedback

Operator feedback should explicitly name which observability signals helped and
which were missing. When the feedback changes incident-response expectations,
open an ADR-004 amendment issue or PR and link the operator finding.

## Exit evidence

Phase B exit requires:

- one external operator completed 30 days of validation;
- all P0 soak findings are closed or explicitly carried forward with a release
  blocker label;
- weekly digests are linked from `LOG.md`;
- relevant ADR-004 amendments are opened or merged;
- roadmap and checklist state are updated in the same PR that records exit
  evidence.
