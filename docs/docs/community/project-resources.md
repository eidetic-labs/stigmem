---
title: Project Resources
sidebar_label: Project Resources
description: Community engagement paths for the Stigmem project — how to contribute, review, or run a validation node.
audience: Evaluator
---

# Project Resources

*Audience: potential contributors, engineers, security researchers, applied researchers, and candidate operators.*

---

Stigmem is in the `v0.9.0aN` alpha line: useful for review, adapter work,
single-organization experiments, and external validation, but not yet recommended
for production cross-organization federation. The most valuable contributions
right now are small, evidence-producing improvements that make the protocol more
testable, auditable, and easier to adopt.

## Contributor entry points

| Path | Start here | Good first work |
|---|---|---|
| Reference node | [Architecture](../reference/architecture/) and [single-host node](../reference/architecture/single-host-node) | Focused tests, docs corrections, small route/CLI fixes |
| Federation | [Federated network](../reference/architecture/federated-network) and [federation concepts](../concepts/federation/) | Scope/audit examples, demo polish, conformance gaps |
| Security review | [Security architecture](../security/) and [threat model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md) | Evidence links, runbook clarity, safe test cases |
| Plugin ecosystem | [Plugin author guide](../guides/plugins/author-guide) and [Adapter ABI](../spec/adapter-abi) | Plugin docs examples, lifecycle tests, fixture improvements |
| Docs and onboarding | [Contributing](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md) and [Roadmap](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md) | Glossary entries, quickstart troubleshooting, issue-template polish |

Starter work is labeled
[`good first issue`](https://github.com/eidetic-labs/stigmem/issues?q=is%3Aissue%20is%3Aopen%20label%3A%22good%20first%20issue%22).
Pick one issue, keep the PR narrow, and include the focused validation you ran.

## Demos to run first

From a repository checkout:

```bash
make demo
make demo-attack
```

`make demo` starts two local nodes, registers them as peers, asserts a fact on
node A, verifies replication on node B, prints federation audit entries, and
tears the cluster down.

`make demo-attack` demonstrates malicious-peer rejection: unauthorized scope
writes and source-forged facts are rejected, audited, and not stored.

## Operator validation

Teams interested in running a node during external validation should open an
[operator candidate issue](https://github.com/eidetic-labs/stigmem/issues/new?template=operator_candidate.yml).
Keep infrastructure details, secrets, and private organization data out of the
public issue; the public thread should describe the validation shape and the
questions you want to answer.

## Security research

Security researchers should read [SECURITY.md](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md)
before filing anything. Public issues are appropriate for security documentation,
safe-harbor questions, or already-public advisory follow-up. Active
vulnerabilities, exploit details, secrets, and private operator findings should
use the private disclosure path.

## Community norms

Stigmem is an open protocol project. All contributors and collaborators are
expected to follow the [Code of Conduct](https://github.com/eidetic-labs/stigmem/blob/main/CODE_OF_CONDUCT.md).

Key principles:

- **Spec changes go through the RFC process.** Wire format, namespace, and federation semantics changes require review before merging.
- **Working evidence beats broad claims.** Prototypes, tests, reproducible demos, and conformance vectors are more persuasive than prose alone.
- **Protocol-layer focus.** Stigmem provides a shared substrate; adapters and agent tools build on top of it.
