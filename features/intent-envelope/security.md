# Intent Envelope Security

## Threat Model Delta

Intent envelope would make agent goals, constraints, handoffs, abandon events,
and escalations explicit protocol data. That can improve auditability, but it
also creates a new place where untrusted content could be mistaken for
operational instruction or authority.

## Owned Risks

None currently identified. The feature is deferred and has no implementation.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-05 prompt injection | Envelope contents could be recalled into agent context and interpreted as trusted intent. | Any reintroduction must preserve content/instruction separation and adapter rendering rules. |
| R-15 instruction-authoring authority | Envelope facts could become a second instruction-admission path if treated as operational directives. | Require explicit envelope write authority and conformance vectors before enabling. |

## Operator Scenarios

- Do not treat envelope-shaped facts as instructions unless an explicit
  promotion policy exists.
- Review adapter behavior before allowing envelope contents into privileged
  prompts or tool plans.

## Conformance Pointers

Required vectors before promotion:

- untrusted envelope facts render as content, not instructions;
- envelope write authority is distinct from ordinary fact write authority;
- handoff/escalation payloads cannot bypass capability checks.

## Residual Risk

The feature should remain deferred until its security boundary is specified and
tested against ADR-003 and R-15.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
