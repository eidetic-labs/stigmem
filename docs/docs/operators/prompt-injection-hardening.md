---
title: Prompt-Injection Hardening
audience: Operator
---

# Prompt-Injection Hardening

Stigmem treats recalled facts as data, not instructions. The node enforces the
protocol-side boundary, but operators still choose the adapters and models that
consume recalled content. This guide captures the current Phase B operating
posture while ADR-015 certification work continues.

## Trust Boundary

| Layer | Responsibility | Status |
| --- | --- | --- |
| L1 origin tagging | Facts retain source identity and scope metadata | Implemented in core. |
| L2 federation receive | Federated instruction-typed facts are denied or quarantined | Implemented in core. |
| L3 recall channel separation | Recall responses separate content from system/developer directives | Implemented in core and adapters under active support. |
| L4 adapter contract | Adapters must preserve the channel boundary when building prompts | Verified by conformance and regression tests. |
| L5 system-prompt directive | The model must honor the adapter's directive | Measured by ADR-015 certification. |
| L6 model behavior | The model must refuse injected behavioral instructions in recalled data | Measured by ADR-015 certification. |

## Current Operator Guidance

- Use the narrowest read and write scopes that satisfy the agent's task.
- Do not grant `instruction:write` unless the agent is explicitly responsible
  for authoring instruction facts.
- Prefer adapters that consume channel-separated recall output directly.
- Treat all live models as uncertified until public ADR-015 certification
  results exist.
- For cross-organization federation workloads, document the accepted risk if an
  uncertified model is used.

## Running the Offline Harness

The offline harness validates the corpus, result schema, and tier calculation:

```sh
uv run python scripts/run_adversarial_conformance.py
```

This does not certify a live model. It is a local readiness check for the
framework used by provider-backed certification runs.

When you are ready to test a live model, use `--provider openai`,
`--provider anthropic`, or `--provider ollama` with the model and credential
configuration described in the model-certification page. Treat the generated
JSON as evidence for review, not as an automatic project certification.

## When Live Certifications Land

Use the model certification page to choose a model tier:

- **Certified:** preferred for cross-organization federation workloads.
- **Provisional:** acceptable for single-organization or lower-risk deployments.
- **Uncertified:** requires explicit risk acceptance.

Re-run certification when the corpus version changes or when a provider changes
the model version used in production.
