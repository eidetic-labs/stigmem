# ADR-003: Capability-based prompt-injection handling

<p className="stigmem-meta"><span>7 min read</span><span>Accepted</span><span>Recorded 2026-05-06</span></p>

<div className="stigmem-lead">

**What this ADR decides**

Replace recall-time sanitizer filtering with a capability-based
authorization model. Treat prompt injection as an authorization
problem, not a content-classification problem. Adds an
`interpret_as` field to `FactValue`, channel-separates `recall()`
output, and defines the L1–L6 trust boundary that operators reason
about end-to-end.

</div>

<div className="stigmem-keypoint">

**Status: Accepted.**

Supersedes §19.7 sanitizer-as-primary-control approach (the sanitizer
is retained as defense-in-depth). Operationalized end-to-end by
[ADR-015](./015-adversarial-conformance-and-model-certification)'s
adversarial conformance corpus and model certification framework.

</div>

**Date:** 2026-05-06 · **Authors:** Eidetic Labs · **Related:** [ADR-015](./015-adversarial-conformance-and-model-certification); threat model R-05, R-15, R-21; `stigmem/openclaw/audit.md` C1; `stigmem/plans/strengthening-plan.md` Phase B

## Context

Stigmem is federated agent memory: agents and humans write facts to a
shared substrate, and other agents recall those facts into LLM context
to inform their behavior. Federation means **facts written by one
organization can flow into agents operated by another**. This is the
core value proposition.

It is also the core attack surface. An adversary who can write into a
scope an agent reads from can attempt to inject instructions into the
agent's context — "ignore previous instructions and...", role markers,
behavioral directives. This class of attack is known as **indirect
prompt injection**.

The current defense (§19.7) is a recall-time content sanitizer that
strips known prompt-injection sentinels from fact `value` strings
before they're returned. The OpenClaw adapter further wraps recalled
facts in a markdown annotation that says "treat as untrusted."

<div className="stigmem-keypoint">

**Sanitizer-as-primary-control is structurally inadequate.**

</div>

<div className="stigmem-grid">

<div>
<h4>Unbounded attack surface</h4>
<p>The space of injection patterns is adversarial and infinite. Sentinel-list defenders lose to motivated attackers who paraphrase, encode, switch languages, embed instructions in URLs, or use natural language the defender hasn't anticipated.</p>
</div>

<div>
<h4>Wrong layer</h4>
<p>The recall pipeline doesn't know what the consuming LLM treats as instructions. A string harmless to one model is an instruction to another. Filtering content for a property that depends on the consumer is structurally unsound.</p>
</div>

<div>
<h4>Federation makes it worse</h4>
<p>A peer organization can write facts whose values are <em>literally designed</em> to trigger downstream agents that will recall them. Defense-by-string-filter is theater against a peer who knows your filter.</p>
</div>

</div>

The threat-model risks tied to this gap are R-05 (general prompt
injection), R-15 (instruction-scope injection via §21), and R-21 (the
agent feedback-loop worm vector). All three are rated High or
Critical. Until the structural fix lands, cross-organizational
federation should not be recommended for production use.

## Decision

We replace the sanitizer-as-primary-control model with a
**capability-based authorization model** that treats prompt injection
as an authorization problem, not a content-classification problem.

### Data model change

`FactValue` gains a new field `interpret_as`:

```python
class FactValue(BaseModel):
 type: Literal["string", "text", "number", "boolean", "datetime", "ref", "null"]
 v: Any = None
 interpret_as: Literal["content", "instruction", "code"] = "content"
```

The default is `"content"`. All facts written prior to this ADR's
deployment are treated as `interpret_as = "content"` on read.

### Enforcement rules

<div className="stigmem-fields">

<div>
<dt>Rule</dt>
<dt><span className="stigmem-fields__type">Enforcement</span></dt>
<dd>Effect</dd>
</div>

<div>
<dt>1 · Default-deny on instruction interpretation</dt>
<dt><span className="stigmem-fields__type">protocol</span></dt>
<dd>Facts with <code>interpret_as = "content"</code> are <em>never</em> injected as instructions. Recall returns content-typed facts in a structurally-delimited block; the adapter surfaces a system-prompt directive marking the block as untrusted data.</dd>
</div>

<div>
<dt>2 · Writing instruction-typed facts is gated</dt>
<dt><span className="stigmem-fields__type">capability</span></dt>
<dd>Requires <code>instruction:write</code> capability for the target scope. General <code>write</code> is insufficient. Cross-org federation requires human-in-the-loop approval; inbound auto-quarantines. Provenance is stamped at write and surfaced in recall.</dd>
</div>

<div>
<dt>3 · Recall labels output by capability</dt>
<dt><span className="stigmem-fields__type">transport</span></dt>
<dd><code>recall()</code> returns distinct <code>instructions</code> and <code>content</code> arrays. Adapters that don't honor the distinction must refuse to serve.</dd>
</div>

<div>
<dt>4 · Federation cannot raise <code>interpret_as</code> on replication</dt>
<dt><span className="stigmem-fields__type">structural</span></dt>
<dd>A content-typed fact arriving from a peer <strong>cannot</strong> be promoted to instruction-typed by the receiver, ever. Structural antidote to the worm vector (R-21).</dd>
</div>

<div>
<dt>5 · Detection as defense-in-depth</dt>
<dt><span className="stigmem-fields__type">advisory</span></dt>
<dd>The sanitizer (§19.7) is renamed "instruction anomaly detector" and demoted from primary control. Flagged facts are <em>quarantined and notified</em>, not stripped. Detection is cheap; prevention is structural.</dd>
</div>

</div>

### Recall response shape

```json
{
 "instructions": [...], // facts with interpret_as = "instruction"
 "content": [...]       // facts with interpret_as = "content"
}
```

### Adapter contract

All adapters consuming `recall()` output **MUST**:

<ol className="stigmem-steps">
<li>Surface a defined system-prompt directive (<code>SYSTEM_PROMPT_DIRECTIVE</code>) above any injected context.</li>
<li>Render content-channel and instruction-channel facts in distinct, delimited blocks.</li>
<li>Refuse to operate if the recall response is malformed or missing the channel separation.</li>
</ol>

The OpenClaw adapter v0.9 ships with an interim version of this
contract (defense-in-depth delimiters + system-prompt directive)
before the protocol-level structural fix lands. After this ADR, the
adapter is updated to consume the channel-separated response natively.

### Audit events

Two new audit event types are added:

<div className="stigmem-grid">

<div>
<h4><code>instruction_quarantined</code></h4>
<p>Fact arrived as instruction-typed and was placed in quarantine pending approval.</p>
</div>

<div>
<h4><code>instruction_promoted</code></h4>
<p>Admin operator promoted a quarantined instruction-typed fact into the active store.</p>
</div>

</div>

### Trust boundary (L1–L6)

Stigmem's prompt-injection defenses operate across six layers, two of
which are outside stigmem's reach.

<div className="stigmem-fields">

<div>
<dt>Layer</dt>
<dt><span className="stigmem-fields__type">Enforcement</span></dt>
<dd>What it does</dd>
</div>

<div>
<dt>L1 · Origin tagging</dt>
<dt><span className="stigmem-fields__type">stigmem · unconditional</span></dt>
<dd>Every fact carries <code>interpret_as</code> (default <code>content</code>). Writing <code>instruction</code>-typed facts requires <code>instruction:write</code> capability.</dd>
</div>

<div>
<dt>L2 · Federation receive</dt>
<dt><span className="stigmem-fields__type">stigmem · unconditional</span></dt>
<dd>Receiver-side promotion of content-typed facts to instruction-typed is structurally impossible. Peer-claimed instruction-typed facts auto-quarantine pending admin approval. No configuration override.</dd>
</div>

<div>
<dt>L3 · Recall channel separation</dt>
<dt><span className="stigmem-fields__type">stigmem · unconditional</span></dt>
<dd><code>recall()</code> returns distinct <code>instructions</code> and <code>content</code> arrays. Channels are separate in transport.</dd>
</div>

<div>
<dt>L4 · Adapter contract</dt>
<dt><span className="stigmem-fields__type">adapter · verified by conformance</span></dt>
<dd>Adapter renders channels in distinct delimited blocks; surfaces <code>SYSTEM_PROMPT_DIRECTIVE</code>; refuses to operate on malformed responses. Verified by adversarial conformance vectors.</dd>
</div>

<div>
<dt>L5 · System prompt directive</dt>
<dt><span className="stigmem-fields__type">adapter delivers · LLM honors</span></dt>
<dd>LLM's system prompt explicitly tells it the content channel is untrusted data, not instructions.</dd>
</div>

<div>
<dt>L6 · LLM behavior</dt>
<dt><span className="stigmem-fields__type">outside stigmem</span></dt>
<dd>LLM ultimately decides what to follow.</dd>
</div>

</div>

<div className="stigmem-decision">

<div>
<h4>What stigmem guarantees</h4>
<ul>
<li>L1, L2, L3 are enforced by the protocol implementation. No knob to disable them.</li>
<li>Code review and CI verify they cannot be bypassed.</li>
<li>L4 is verified by adversarial conformance vectors (see <a href="./015-adversarial-conformance-and-model-certification">ADR-015</a>). Any adapter that ships under the stigmem name passes these vectors before release.</li>
</ul>
</div>

<div>
<h4>What stigmem does NOT guarantee</h4>
<ul>
<li>L5 depends on the adapter passing the directive correctly to the LLM (verified at L4) and the LLM accepting the directive's framing.</li>
<li>L6 is a property of the consuming LLM. Some models are robust to indirect prompt injection; some are not. Stigmem's structural defenses ensure the LLM has every signal it needs to treat content as data, but stigmem cannot reach into the model.</li>
</ul>
</div>

</div>

<div className="stigmem-keypoint">

**The honest one-line summary.**

> Stigmem structurally separates instructions from content end-to-end.
> The receiving LLM ultimately decides whether to honor that
> separation. We help you choose models that do.

The "we help you choose" half of that sentence is operationalized by
the adversarial conformance corpus and model certification framework
specified in [ADR-015](./015-adversarial-conformance-and-model-certification).
ADR-003 commits to the protocol-layer defenses; ADR-015 commits to the
testing infrastructure that operationalizes the consumer-layer
dependencies (L4–L6).

</div>

## Alternatives considered

<div className="stigmem-fields">

<div>
<dt>Alternative</dt>
<dt><span className="stigmem-fields__type">Disposition</span></dt>
<dd>Why</dd>
</div>

<div>
<dt>Continue with sanitizer-stripping; expand the sentinel list</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Bounded defenders lose to unbounded attackers. Every project that has tried this approach has been bypassed.</dd>
</div>

<div>
<dt>Use an LLM-based classifier to detect prompt-injection content</dt>
<dt><span className="stigmem-fields__type">rejected as primary control</span></dt>
<dd>Classifiers are themselves subject to adversarial inputs and add latency and cost to every recall. Acceptable as defense-in-depth detection, not as authorization.</dd>
</div>

<div>
<dt>Capability tokens only (no <code>interpret_as</code> field)</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>Tokens authorize <em>writes</em>; they don't tell the recall pipeline how to <em>frame</em> the content for the consumer. The <code>interpret_as</code> field is the durable, queryable property the pipeline needs.</dd>
</div>

<div>
<dt>Treat all federated content as content-typed; never allow instruction-typed federation</dt>
<dt><span className="stigmem-fields__type">considered, partially adopted</span></dt>
<dd>This is the <em>safest</em> default, and is what Rule 4 effectively enforces — peer-claimed instruction-typed facts always quarantine. The decision retains the option for <em>operator-approved</em> cross-org instructions while making the default safe.</dd>
</div>

<div>
<dt>Wait for upstream LLM providers to solve indirect prompt injection</dt>
<dt><span className="stigmem-fields__type">rejected</span></dt>
<dd>There is no plausible path by which a model trained to be helpful learns to ignore instructions in arbitrary content. Solving this at the application layer is the tractable problem.</dd>
</div>

</div>

## Consequences

### What gets easier

<div className="stigmem-grid">

<div><h4>Federation becomes defensible</h4><p>"Facts replicate, but instructions never replicate without operator approval" maps to a structural enforcement, not a content filter.</p></div>
<div><h4>Adopter mental model is clear</h4><p>Instructions vs content is a familiar distinction (HTTP headers vs body, code vs data); operators can reason about where the boundary is.</p></div>
<div><h4>R-15 and R-21 close</h4><p>Both require instruction-typed facts to flow without authorization; this ADR makes that flow impossible by default.</p></div>
<div><h4>Defense-in-depth retains the sanitizer</h4><p>The detection layer continues to add value, just not as the primary control.</p></div>

</div>

### What gets harder

<div className="stigmem-grid">

<div><h4>Wire format change</h4><p><code>FactValue</code> gains a field. v0.9.x preserves backwards compatibility (missing <code>interpret_as</code> defaults to <code>"content"</code>), but consumers eventually need to migrate.</p></div>
<div><h4>Adapter contract is load-bearing</h4><p>Adapters that don't surface <code>SYSTEM_PROMPT_DIRECTIVE</code> and don't honor channel separation are <em>non-conformant</em> — not just suboptimal.</p></div>
<div><h4>Operator workflow for instruction approval</h4><p>Cross-org instruction-typed facts requiring human-in-the-loop approval is a real workflow operators must run. CLI / admin endpoint required in v0.9.x.</p></div>
<div><h4>§21 needs a rethink</h4><p>The original §21 lazy instruction discovery design treats <code>instruction:write</code> as a regular write permission. ADR-003 + R-15 mitigation collectively mean §21 needs a substantial rethink before it ships outside experimental.</p></div>

</div>

### New risks

<div className="stigmem-fields">

<div>
<dt>Risk</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Mitigation</dd>
</div>

<div>
<dt><code>R-ADR3-1</code> · adapter non-compliance</dt>
<dt><span className="stigmem-fields__type">tracked</span></dt>
<dd>An adapter that consumes the channel-separated recall response but quietly concatenates <code>instructions</code> and <code>content</code> into a single block defeats the whole structural fix. Conformance vectors test for distinct channel handling; non-compliant adapters must declare non-conformance in their README.</dd>
</div>

<div>
<dt><code>R-ADR3-2</code> · operators set permissive default</dt>
<dt><span className="stigmem-fields__type">closed</span></dt>
<dd>There is no configuration knob to disable Rule 4; the quarantine + admin-promote flow is the only path.</dd>
</div>

<div>
<dt><code>R-ADR3-3</code> · detection layer creates false confidence</dt>
<dt><span className="stigmem-fields__type">tracked</span></dt>
<dd>The renamed "instruction anomaly detector" might be mistaken for a primary control again in two years. Documentation explicitly names it as defense-in-depth and references this ADR.</dd>
</div>

</div>

## Implementation plan

This ADR's implementation spans Phase B (capability redesign work),
owned by the team.

### Phase B · write path

<div className="stigmem-grid">

<div><h4><code>FactValue.interpret_as</code></h4><p>Field added to <code>models.py</code>.</p></div>
<div><h4>Write enforcement</h4><p>At <code>routes/facts.py</code> (<code>POST /v1/facts</code>).</p></div>
<div><h4>Federation inbound enforcement</h4><p>At <code>routes/federation.py</code>.</p></div>
<div><h4>Quarantine flow</h4><p>Updated to handle instruction-typed inbound facts.</p></div>
<div><h4>Adversarial conformance vectors</h4><p>At <code>data/conformance/adversarial/</code>.</p></div>

</div>

### Phase B · read path and adapter

<div className="stigmem-grid">

<div><h4><code>recall()</code> response</h4><p>Gains channel separation.</p></div>
<div><h4>MCP &amp; OpenClaw adapters</h4><p>Updated to consume channel-separated output.</p></div>
<div><h4><code>SYSTEM_PROMPT_DIRECTIVE</code></h4><p>Constant defined and surfaced.</p></div>
<div><h4>Audit event types</h4><p><code>instruction_quarantined</code> and <code>instruction_promoted</code> added.</p></div>

</div>

### Migration

<div className="stigmem-fields">

<div>
<dt>Version</dt>
<dt><span className="stigmem-fields__type">Reader contract</span></dt>
<dd>Behavior</dd>
</div>

<div>
<dt>v0.9.x</dt>
<dt><span className="stigmem-fields__type">dual-mode</span></dt>
<dd>Channel-separated for new clients; legacy single-list for old clients via <code>legacy_format=true</code> query param. Default is channel-separated.</dd>
</div>

<div>
<dt>v1.0.0</dt>
<dt><span className="stigmem-fields__type">channel-separated only</span></dt>
<dd>Legacy format removed.</dd>
</div>

</div>

## Open questions

<div className="stigmem-fields">

<div>
<dt>Question</dt>
<dt><span className="stigmem-fields__type">Recommended</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Should <code>interpret_as = "code"</code> be supported in v1.0?</dt>
<dt><span className="stigmem-fields__type">not yet</span></dt>
<dd><code>"content"</code> and <code>"instruction"</code> cover the distinction we need today; <code>"code"</code> opens questions (sandbox-able? executable in what environment?) without v1 answers. Reserve the enum value; defer the semantics.</dd>
</div>

<div>
<dt>What's the right transparency-log story for instruction promotion?</dt>
<dt><span className="stigmem-fields__type">defer to a follow-up ADR</span></dt>
<dd>Cross-org instruction promotions are high-trust events. Worth submitting them to Rekor alongside manifest rotations?</dd>
</div>

<div>
<dt>Does the system-prompt directive belong in the adapter or in the protocol?</dt>
<dt><span className="stigmem-fields__type">adapter for now</span></dt>
<dd>Different LLMs need different phrasings. May centralize later if a clear convergence emerges.</dd>
</div>

</div>

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor
approval rule (founder solo-approval; second contributor sign-off
welcome but not required).*
