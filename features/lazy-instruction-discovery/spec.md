---
spec_id: Spec-X1-Lazy-Instruction-Discovery
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-21
supersedes: pre-reset section 21 lazy instruction discovery material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-06-Capability-Tokens >= 0.1.0-alpha.0
  - Spec-07-Recall-Pipeline >= 0.1.0-alpha.0
---

# Spec-X1-Lazy-Instruction-Discovery

## Scope

Lazy instruction discovery lets agents discover and load instructions on demand
instead of preloading every instruction document at startup. The mechanism has
three runtime components: a boot stub, an instruction manifest, and the
`recall_instruction` interface.

## Boot Stub

The boot stub is the minimal agent preamble loaded unconditionally at session
start. It includes the agent identity, heartbeat contract, manifest URI, and
tool schema needed to request additional instructions.

Boot stubs must stay small and should contain only unconditional operating
constraints. Task-conditional instructions should be loaded through the
manifest and recall path.

## Instruction Manifest

The manifest is a compact index of instruction units. Entries describe unit
names, trigger hints, optional task-type preload commitments, source URI or
path, and token estimates.

The manifest must remain small enough to fit in context and must not become a
replacement for the instruction body itself.

## Instruction Recall

`recall_instruction` retrieves instruction units by intent, manifest hints, and
token budget. Returned material enters instruction context rather than ordinary
task content, which makes this path security-sensitive.

## Security Requirements

Instruction-typed writes require dedicated authority. Federation-inbound
instruction-typed facts must fail closed or enter quarantine until admitted by
operator policy. Cross-agent instruction namespace reads must be denied unless
explicitly authorized.

## Non-Goals

- This feature does not graduate lazy instruction discovery into the default
  supported surface.
- This feature does not bypass ADR-003 prompt-injection constraints.
- This feature does not publish a signed plugin artifact yet.
