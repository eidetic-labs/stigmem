# ADR-003: Capability-based prompt-injection handling

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Supersedes:** §19.7 sanitizer-as-primary-control approach (still retained as defense-in-depth)
**Related:** ADR-015 (adversarial conformance corpus and model certification framework — operationalizes the L4–L6 trust boundary); threat model R-05, R-15, R-21; `stigmem/openclaw/audit.md` C1; `stigmem/plans/strengthening-plan.md` Phase B (capability redesign)

---

## Context

Stigmem is federated agent memory: agents and humans write facts to a shared substrate, and other agents recall those facts into LLM context to inform their behavior. Federation means **facts written by one organization can flow into agents operated by another**. This is the core value proposition.

It is also the core attack surface. An adversary who can write into a scope an agent reads from can attempt to inject instructions into the agent's context — "ignore previous instructions and...", role markers, behavioral directives. This class of attack is known as indirect prompt injection.

The current defense (§19.7) is a recall-time content sanitizer that strips known prompt-injection sentinels from fact `value` strings before they're returned. The OpenClaw adapter further wraps recalled facts in a markdown annotation that says "treat as untrusted."

This approach is structurally inadequate, for three reasons:

1. **The space of injection patterns is unbounded and adversarial.** Sentinel-list defenders lose to motivated attackers who paraphrase, encode, switch languages, embed instructions in URLs, or simply use natural language that the defender hasn't anticipated. Any defender working from a finite blocklist eventually loses.

2. **The defense is at the wrong layer.** The recall pipeline doesn't know what the consuming LLM treats as instructions. A string that's harmless to one model is an instruction to another. Filtering content for a property that depends on the consumer is structurally unsound.

3. **Federation makes it strictly worse.** A peer organization can write facts whose values are *literally designed* to trigger downstream agents that will recall them. Defense-by-string-filter is theater against a peer who knows your filter.

The threat-model risks tied to this gap are R-05 (general prompt injection), R-15 (instruction-scope injection via §21), and R-21 (the agent feedback-loop worm vector). All three are rated High or Critical. Until the structural fix lands, cross-organizational federation should not be recommended for production use.

## Decision

We replace the sanitizer-as-primary-control model with a **capability-based authorization model** that treats prompt injection as an authorization problem, not a content-classification problem.

### Data model change

`FactValue` gains a new field `interpret_as`:

```python
class FactValue(BaseModel):
 type: Literal["string", "text", "number", "boolean", "datetime", "ref", "null"]
 v: Any = None
 interpret_as: Literal["content", "instruction", "code"] = "content"
```

The default is `"content"`. All facts written prior to this ADR's deployment are treated as `interpret_as = "content"` on read.

### Enforcement rules

**Rule 1: Default-deny on instruction interpretation.**
Facts with `interpret_as = "content"` are *never* injected into an LLM context as instructions. The recall pipeline returns content-typed facts in a structurally-delimited block; the consuming adapter is required to surface a system-prompt directive informing the LLM that the block is untrusted data.

**Rule 2: Writing instruction-typed facts is gated.**
Writing a fact with `interpret_as = "instruction"` requires:
- A capability token whose grant explicitly includes `instruction:write` for the target scope. General `write` permission is insufficient.
- For cross-organizational federation: an additional human-in-the-loop approval step. Instruction-typed facts arriving via federation enter the quarantine garden by default; only an admin operator can promote them via the admin API.
- An immutable provenance trace stamped at write time, surfaced in recall responses to the consuming LLM.

**Rule 3: Recall labels output by capability.**
The `recall()` API response gains structured separation:

```json
{
 "instructions": [...], // facts with interpret_as = "instruction"
 "content": [...] // facts with interpret_as = "content"
}
```

The two channels are distinct in transport, in the adapter contract, and in the consuming LLM's context framing. Adapters that don't honor the distinction must refuse to serve.

**Rule 4: Federation cannot raise `interpret_as` on replication.**
A federation peer can write an `interpret_as = "instruction"` fact only if their capability token includes `instruction:write` for the target scope, and the receiving node treats all such inbound facts as quarantined-pending-approval regardless of the peer's claim. **A content-typed fact arriving from a peer cannot be promoted to instruction-typed by the receiver, ever.** This is the structural antidote to the worm vector (R-21).

**Rule 5: Detection as defense-in-depth.**
The existing sanitizer (§19.7) is renamed to "instruction anomaly detector" and demoted from primary control to defense-in-depth. Its role is to flag content-typed facts whose `value` matches structural-instruction heuristics (imperatives, role markers, large prose blocks). Flagged facts don't get stripped; they get *quarantined and notified* to the operator. Detection is cheap; prevention is structural.

### Adapter contract

All adapters consuming `recall()` output MUST:

1. Surface a defined system-prompt directive (`SYSTEM_PROMPT_DIRECTIVE`) above any injected context.
2. Render content-channel and instruction-channel facts in distinct, delimited blocks.
3. Refuse to operate if the recall response is malformed or missing the channel separation.

The OpenClaw adapter v0.9 ships with an interim version of this contract (defense-in-depth delimiters + system-prompt directive) before the protocol-level structural fix lands. After this ADR, the adapter is updated to consume the channel-separated response natively.

### Audit events

Two new audit event types are added:

- `instruction_quarantined`: fact arrived as instruction-typed and was placed in quarantine pending approval.
- `instruction_promoted`: admin operator promoted a quarantined instruction-typed fact into the active store.

### Trust boundary

Stigmem's prompt-injection defenses operate across six layers, two of which are outside stigmem's reach. Operators evaluating stigmem need this boundary explicit to reason about end-to-end risk:

| Layer | What it does | Who enforces |
|---|---|---|
| **L1: Origin tagging** | Every fact carries `interpret_as` (default `content`). Writing `instruction`-typed facts requires `instruction:write` capability. | **Stigmem (unconditional).** |
| **L2: Federation receive** | Receiver-side promotion of content-typed facts to instruction-typed is structurally impossible. Peer-claimed instruction-typed facts auto-quarantine pending admin approval. | **Stigmem (unconditional, no configuration override).** |
| **L3: Recall channel separation** | `recall()` returns distinct `instructions` and `content` arrays. Channels are separate in transport. | **Stigmem (unconditional).** |
| **L4: Adapter contract** | Adapter renders channels in distinct delimited blocks; surfaces `SYSTEM_PROMPT_DIRECTIVE`; refuses to operate on malformed responses. | **Adapter implementation; stigmem verifies via conformance vectors.** |
| **L5: System prompt directive** | LLM's system prompt explicitly tells it the content channel is untrusted data, not instructions. | **Adapter delivers; LLM honors (or doesn't).** |
| **L6: LLM behavior** | LLM ultimately decides what to follow. | **Outside stigmem entirely.** |

**What stigmem guarantees:**
- L1, L2, L3 are enforced by stigmem's protocol implementation. There is no configuration knob to disable them. Code review and CI verify they cannot be bypassed.
- L4 is verified by adversarial conformance vectors (see ADR-015). Any adapter that consumes `recall()` and ships under the stigmem name passes these vectors before release.

**What stigmem does NOT guarantee:**
- L5 depends on the adapter passing the directive correctly to the LLM (verified at L4) and the LLM accepting the directive's framing.
- L6 is an property of the consuming LLM. Some models are robust to indirect prompt injection; some are not. Stigmem's structural defenses ensure the LLM has every signal it needs to treat content as data, but stigmem cannot reach into the model.

**The honest one-line summary, suitable for the docs front page:**
> Stigmem structurally separates instructions from content end-to-end. The receiving LLM ultimately decides whether to honor that separation. We help you choose models that do.

The "we help you choose" half of that sentence is operationalized by the adversarial conformance corpus and model certification framework specified in ADR-015. ADR-003 commits to the protocol-layer defenses; ADR-015 commits to the testing infrastructure that operationalizes the consumer-layer dependencies (L4-L6).

## Alternatives considered

**1. Continue with sanitizer-stripping; expand the sentinel list.** Rejected. Bounded defenders lose to unbounded attackers. Every project that has tried this approach has been bypassed.

**2. Use an LLM-based classifier to detect prompt-injection content.** Rejected as primary control. Classifiers are themselves subject to adversarial inputs and add latency and cost to every recall. Acceptable as defense-in-depth detection, not as authorization.

**3. Capability tokens as the only control (no `interpret_as` field on the data model).** Rejected. Tokens authorize *writes*; they don't tell the recall pipeline how to *frame* the content for the consumer. The `interpret_as` field is the durable, queryable property the recall pipeline needs to make the channel-separation decision.

**4. Treat all federated content as content-typed; never allow instruction-typed federation.** Considered seriously. This is the *safest* default, and it is what the receiver-side rule (Rule 4) effectively enforces — peer-claimed instruction-typed facts always quarantine. The decision retains the option for *operator-approved* cross-org instructions (e.g., a parent organization issuing operational directives to subsidiaries) while making the default safe.

**5. Wait for upstream LLM providers to solve indirect prompt injection.** Rejected. There is no plausible path by which a model trained to be helpful learns to ignore instructions in arbitrary content. Solving this at the application layer is the tractable problem.

## Consequences

### What gets easier

- **Federation becomes defensible.** "Facts replicate, but instructions never replicate without operator approval" is a billboard sentence. It maps to a structural enforcement, not a content filter.
- **Adopter mental model is clear.** Instructions vs content is a familiar distinction (HTTP headers vs body, code vs data); operators can reason about where the boundary is and where it isn't.
- **R-15 and R-21 close.** Instruction-scope injection and the agent feedback-loop worm both require instruction-typed facts to flow without authorization; this ADR makes that flow impossible by default.
- **Defense-in-depth retains the sanitizer.** The detection layer continues to add value, just not as the primary control.

### What gets harder

- **Wire format change.** `FactValue` gains a field. v0.9.x preserves backwards compatibility (missing `interpret_as` defaults to `"content"`), but consumers eventually need to migrate.
- **Adapter contract is now load-bearing.** Adapters that don't surface `SYSTEM_PROMPT_DIRECTIVE` and don't honor channel separation are *non-conformant* — not just suboptimal. We need conformance vectors that adapters can self-test against.
- **Operator workflow for instruction approval.** Cross-org instruction-typed facts requiring human-in-the-loop approval is a real workflow operators must run. We need to ship a CLI or admin endpoint for this in v0.9.x.
- **The §21 lazy instruction discovery feature, deferred to v2.0.0-experimental, must be redesigned around this model before re-introduction.** The original §21 design treats `instruction:write` as a regular write permission; ADR-003 + R-15's mitigation (dedicated `instruction_write` permission tier) collectively mean §21 needs a substantial rethink before it ships outside experimental.

### New risks

- **R-ADR3-1: adapter non-compliance.** An adapter that consumes the channel-separated recall response but quietly concatenates `instructions` and `content` into a single block defeats the whole structural fix. Mitigation: conformance vectors test for distinct channel handling; non-compliant adapters must declare themselves non-conformant in their README.
- **R-ADR3-2: operators set permissive default.** An operator who configures the receiver to auto-promote inbound instruction-typed facts without review nullifies Rule 4. Mitigation: there is no configuration knob to disable Rule 4; the quarantine + admin-promote flow is the only path.
- **R-ADR3-3: detection layer creates false confidence.** The renamed "instruction anomaly detector" might be mistaken for a primary control again in two years. Mitigation: documentation explicitly names it as defense-in-depth and references this ADR.

## Implementation plan

This ADR's implementation spans Phase B (capability redesign work), owned by the team.

**Phase B (capability redesign) — write path:**
- `FactValue.interpret_as` field added to `models.py`.
- Write enforcement at `routes/facts.py` (`POST /v1/facts`).
- Write enforcement at `routes/federation.py` (federation inbound).
- Quarantine flow updated to handle instruction-typed inbound facts.
- Adversarial conformance vectors at `data/conformance/adversarial/`.

**Phase B (capability redesign) — read path and adapter:**
- `recall()` response gains channel separation.
- MCP adapter and OpenClaw adapter updated to consume channel-separated output.
- `SYSTEM_PROMPT_DIRECTIVE` constant defined and surfaced.
- Audit event types `instruction_quarantined` and `instruction_promoted` added.

**Migration:**
- v0.9.x: dual-mode reads (channel-separated for new clients; legacy single-list for old clients via `legacy_format=true` query param). Default is channel-separated.
- v1.0.0: legacy format removed.

## Open questions

- **Should `interpret_as = "code"` be supported in v1.0?** Recommended: not yet. `"content"` and `"instruction"` cover the distinction we need today; `"code"` opens questions (sandbox-able? executable in what environment?) that don't have v1 answers. Reserve the enum value; defer the semantics.

- **What's the right transparency-log story for instruction promotion?** Cross-org instruction promotions are high-trust events. Worth submitting them to Rekor alongside manifest rotations? Defer to a follow-up ADR.

- **Does the system-prompt directive belong in the adapter or in the protocol?** Adapter for now (different LLMs need different phrasings). May centralize later if a clear convergence emerges.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*