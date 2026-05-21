# Memory Garden Advanced ACL Security

## Threat Model Delta

Memory Garden advanced ACL can narrow or widen the R-21 feedback-loop risk
depending on its final design. A hardened design should make session read/write
boundaries explicit and auditable. A loose design could authorize an agent to
write back into the same garden that supplied prompt-influencing facts.

## Owned Risks

None currently identified. Any future owned R-XX risk must be added to the
unified threat model and this feature record in the same PR.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-21 agent feedback-loop worm | Garden ACLs are one candidate boundary for preventing write-back into scopes or gardens that influenced the same agent session. | Treat advanced ACL as incomplete until same-session read/write graph isolation and audit evidence are validated. |

## Operator Scenarios

- Do not treat garden ACLs as a complete R-21 mitigation until per-session
  read/write graph isolation is designed and tested.
- Review any feature design that grants writer keys based on recent recall
  context as security-sensitive.

## Conformance Pointers

Required adversarial vectors before promotion:

- an agent cannot write into a garden it read from in the same protected
  session;
- attempted graph-isolation bypasses leave audit evidence;
- outbound federation excludes facts derived from transitively recalled
  content until explicitly approved.

## Residual Risk

Gate 1 remains open. The security delta must explicitly say whether the feature
implements, supports, or merely coexists with the R-21 mitigation design.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
