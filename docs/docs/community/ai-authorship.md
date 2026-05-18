---
id: ai-authorship
title: AI Authorship Disclosure
sidebar_label: AI Authorship
description: How Stigmem discloses AI-assisted work and calibrates review expectations.
---

# AI Authorship Disclosure

*Audience: contributors, adopters, security reviewers, and operators.*

---

Stigmem is built by two contributors with heavy AI-coding assistance. We disclose this because a category whose product is trust should not quietly hide where the work came from.

This is a calibration aid, not a defect notice. It helps readers decide where to apply extra verification before relying on Stigmem in their own workload.

## Deeper human review

These paths receive line-by-line human review:

- `spec/` — protocol specification text
- `docs/adr/` — Architecture Decision Records
- `LIMITATIONS.md`, `SECURITY.md`, `MAINTAINERS.md`, and the root `README.md`
- Threat-model entries in `spec/security/` and rendered security docs

## Lighter human review

These paths receive high-level direction and spot checks:

- `node/src/` — reference node implementation
- `adapters/` — adapter implementations
- `sdks/` — SDK stubs
- UI scaffolding and experimental surfaces
- Test suites
- Documentation pages outside the spec, ADRs, and security posture docs

## Contributor expectation

When a PR includes AI-generated code or prose, say so in the PR description. The project does not reject AI-assisted contributions; it calibrates review effort. Reviewers should verify behavior against the spec, run the relevant conformance or test suite, and audit higher-risk paths before merging.

The canonical source copy for this disclosure is also maintained in [`README.md`](https://github.com/eidetic-labs/stigmem/blob/main/README.md#ai-authorship-disclosure) and [`CONTRIBUTING.md`](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md#ai-authorship-disclosure).
