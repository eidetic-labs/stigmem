---
title: Prompt-Injection Hardening
audience: Operator
---

# Prompt-Injection Hardening

<p className="stigmem-meta"><span>3 min read</span><span>Node operator</span><span>Phase B · v0.9.0aN</span></p>

<div className="stigmem-lead">

**What this guide covers**

Stigmem treats recalled facts as data, not instructions. The node
enforces the protocol-side boundary, but operators still choose the
adapters and models that consume recalled content. This guide
captures the current Phase B operating posture while ADR-015
certification work continues.

</div>

## Trust boundary

<div className="stigmem-fields">

<div>
<dt>Layer</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Responsibility</dd>
</div>

<div>
<dt>L1 origin tagging</dt>
<dt><span className="stigmem-fields__type">implemented (core)</span></dt>
<dd>Facts retain source identity and scope metadata.</dd>
</div>

<div>
<dt>L2 federation receive</dt>
<dt><span className="stigmem-fields__type">implemented (core)</span></dt>
<dd>Federated instruction-typed facts are denied or quarantined.</dd>
</div>

<div>
<dt>L3 recall channel separation</dt>
<dt><span className="stigmem-fields__type">implemented (core+adapters)</span></dt>
<dd>Recall responses separate content from system/developer directives.</dd>
</div>

<div>
<dt>L4 adapter contract</dt>
<dt><span className="stigmem-fields__type">verified (conformance)</span></dt>
<dd>Adapters must preserve the channel boundary when building prompts.</dd>
</div>

<div>
<dt>L5 system-prompt directive</dt>
<dt><span className="stigmem-fields__type">measured (ADR-015)</span></dt>
<dd>The model must honor the adapter's directive.</dd>
</div>

<div>
<dt>L6 model behavior</dt>
<dt><span className="stigmem-fields__type">measured (ADR-015)</span></dt>
<dd>The model must refuse injected behavioral instructions in recalled data.</dd>
</div>

</div>

## Current operator guidance

<div className="stigmem-grid">

<div><h4>Narrowest scopes</h4><p>Use the narrowest read and write scopes that satisfy the agent's task.</p></div>
<div><h4>No `instruction:write`</h4><p>Do not grant unless the agent is explicitly responsible for authoring instruction facts.</p></div>
<div><h4>Channel-separated adapters</h4><p>Prefer adapters that consume channel-separated recall output directly.</p></div>
<div><h4>Treat models as uncertified</h4><p>Until public ADR-015 results exist in <code>data/conformance/adversarial/results/index.json</code>.</p></div>
<div><h4>Document accepted risk</h4><p>For cross-organization federation workloads using an uncertified model.</p></div>

</div>

## Running the offline harness

The offline harness validates the corpus, result schema, and tier calculation:

```sh
uv run python scripts/run_adversarial_conformance.py
```

<div className="stigmem-keypoint">

**This does not certify a live model.**

It is a local readiness check for the framework used by
provider-backed certification runs. When you are ready to test a
live model, use `--provider openai`, `--provider anthropic`, or
`--provider ollama` with the credential configuration described in
the model-certification page. Treat the generated JSON as evidence
for review, not as an automatic project certification.

</div>

## When live certifications land

<div className="stigmem-fields">

<div>
<dt>Tier</dt>
<dt><span className="stigmem-fields__type">Use case</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Certified</dt>
<dt><span className="stigmem-fields__type">preferred</span></dt>
<dd>For cross-organization federation workloads.</dd>
</div>

<div>
<dt>Provisional</dt>
<dt><span className="stigmem-fields__type">acceptable</span></dt>
<dd>For single-organization or lower-risk deployments.</dd>
</div>

<div>
<dt>Uncertified</dt>
<dt><span className="stigmem-fields__type">explicit risk acceptance</span></dt>
<dd>Requires documented accepted risk.</dd>
</div>

</div>

Re-run certification when the corpus version changes or when a provider changes the model version used in production. Published certified and provisional results also expire after 90 days unless a newer reviewed result replaces them.
