# Lazy Instruction Discovery Security

## Owned Risks

### R-15: Instruction-scope write authority

Lazy instruction discovery lets agents load instruction-typed facts as
operational instructions at boot. Any key that can write facts with
`interpret_as="instruction"` can therefore author instructions for agents that
consume those facts.

Current controls include scope-based access control, dedicated
`instruction:write` local-write gating, recall channel separation through
`interpret_as`, federation-inbound quarantine for instruction-typed facts, and
boot-stub embedding requirements for unconditional prohibitions.

Required mitigation remains an admission boundary for lazy instruction use:
admin-approved promotion policy and protocol adversarial vectors for the full
path.

## Contributed Risks

### R-21: Agent feedback-loop worm

Lazy instruction discovery contributes to R-21 because instruction facts are
one path by which prompt-injected or malicious content can become durable agent
behavior and then cause additional attacker-chosen writes.

## Threat Model Delta

This feature adds the agent-runtime-to-instruction-recall trust boundary. The
security-sensitive transition is content moving from persisted facts into
instruction context. That transition is higher impact than ordinary recall
because it happens before task processing and can affect all subsequent agent
decisions.

## Conformance Pointers

Required adversarial vectors before promotion:

- instruction-typed fact write without `instruction:write` capability returns
  403;
- federation inbound instruction-typed facts are quarantined by default;
- boot-time instruction recall excludes quarantined facts;
- cross-agent instruction namespace reads are denied.

## Residual Risk

The feature cannot graduate while R-15 remains open, because the original
design does not distinguish ordinary fact writes from instruction-authoring
writes strongly enough for supported production use.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
