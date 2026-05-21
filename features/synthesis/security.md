# Synthesis Security

## Threat Model Delta

Synthesis turns multiple facts into a compact summary that agents may place in
context. That makes source attribution, contradiction flags, and prompt
rendering security-sensitive. A synthesized summary must not erase uncertainty
or turn untrusted facts into operational instructions.

## Owned Risks

None currently identified.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-05 prompt injection | Synthesized summaries may carry adversarial fact content into agent context. | Preserve content/instruction separation and render provenance/contradiction state. |
| R-21 agent feedback-loop worm | Agents may write new facts based on synthesized summaries of prior recalled facts. | Preserve session/provenance boundaries when synthesis output influences writes. |

## Operator Scenarios

- Treat synthesized summaries as derived content, not operator instructions.
- Keep contradiction indicators visible to consumers.
- Preserve source fact provenance when synthesis output drives writes.

## Conformance Pointers

Required vectors before promotion:

- synthesized output preserves contradiction flags;
- untrusted source content remains in the content channel;
- write-back based on synthesized output carries provenance.

## Residual Risk

Synthesis should remain experimental until adapter rendering and provenance
handling are validated against ADR-003 and R-21.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
