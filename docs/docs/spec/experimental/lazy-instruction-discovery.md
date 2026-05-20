---
spec_id: Spec-X1-Lazy-Instruction-Discovery
version: 0.1.0-alpha.0
status: Experimental
applies_to: stigmem v0.9.0bN
last_updated: 2026-05-14
supersedes: pre-reset §21 lazy instruction discovery material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-06-Capability-Tokens >= 0.1.0-alpha.0
  - Spec-07-Recall-Pipeline >= 0.1.0-alpha.0
title: §21. Lazy Instruction Discovery
sidebar_label: §21 Lazy Instruction Discovery
audience: Spec
description: "Stigmem spec section 21 — Boot stub + manifest + on-demand recall for token-efficient agent instruction loading."
stability: experimental
since: 0.9.0a1
---

# §21. Lazy Instruction Discovery {#section-21}

<p className="stigmem-meta"><span>12 min read</span><span>Spec contributor · Agent runtime author</span><span>Experimental · v0.9.0bN</span></p>

<div className="stigmem-lead">

**What this section covers**

How agents discover and load their instructions on demand rather
than preloading every instruction document at startup. Three
runtime components — a **boot stub**, an **instruction manifest**,
and the **`recall_instruction` tool** — plus an off-path **discovery
audit** for continuous retrieval-quality evaluation.

</div>

**Status:** Experimental / opt-in source package on `main`

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for lazy instruction discovery.

:::caution EXPERIMENTAL
The boot-stub schema and instruction-manifest format are not yet finalized and may change in a future minor release. Do not deploy lazy-discovered instructions in production agents handling sensitive data or irreversible tool use until this section reaches GA. Always pin `instructions_manifest_uri` to a trusted, integrity-verified source.
:::

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** Experimental. Implementation source is opt-in and remains outside the supported default install.

---

### §21.1 Boot Stub {#section-21-1}

The boot stub is the minimal agent preamble loaded unconditionally at the start of every heartbeat or session. Its purpose is to give the agent enough context to function and to provide handles for lazy-loading the rest of its instructions.

#### §21.1.1 Required Content {#section-21-1-1}

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Role</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>agent_id</code></dt>
<dt><span className="stigmem-fields__type">identity</span></dt>
<dd>Stable UUID that uniquely identifies this agent within the deployment.</dd>
</div>

<div>
<dt><code>agent_role</code></dt>
<dt><span className="stigmem-fields__type">human label</span></dt>
<dd>e.g. <code>"CTO"</code>, <code>"ResearchScientist"</code>.</dd>
</div>

<div>
<dt><code>heartbeat_contract</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd><code>instruction:</code> fact URI pointing to the heartbeat procedure document.</dd>
</div>

<div>
<dt><code>manifest_uri</code></dt>
<dt><span className="stigmem-fields__type">URI</span></dt>
<dd><code>instruction:</code> scope URI for the instruction manifest.</dd>
</div>

<div>
<dt><code>recall_tool_schema</code></dt>
<dt><span className="stigmem-fields__type">inline schema</span></dt>
<dd>JSON Schema for <code>recall_instruction</code>; MUST be present so the agent can invoke it without a separate fetch.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Rules that apply unconditionally on every heartbeat MAY be embedded directly in the boot stub body.**

This is the primary mitigation against chronic instruction-scope
misses (§21.5.3 limitation note): a rule that is always in context
cannot be silently missed by a retrieval failure. Deployments SHOULD
classify each instruction unit as "always applicable" (candidate for
boot stub embedding) or "task-conditional" (lazy-load via manifest).

</div>

#### §21.1.2 Wire Format {#section-21-1-2}

The boot stub MUST be serialized as a markdown document with YAML frontmatter:

```markdown
---
agent_id: "8e0ed057-bcd8-4f8f-92ee-c046c55b64e9"
agent_role: "CTO"
heartbeat_contract: "instruction:acme/heartbeat-contract/v1"
manifest_uri: "instruction:acme/agent/cto/manifest/v1"
stub_version: 1
generated_at: "2026-05-04T00:00:00Z"
adapter_profile: "paperclip-claude-code"
migration_mode: "stigmem"
---

# Agent Boot Stub

You are **CTO** (id: `8e0ed057-bcd8-4f8f-92ee-c046c55b64e9`).

Your heartbeat procedure is at `instruction:acme/heartbeat-contract/v1`.
Your instruction manifest is at `instruction:acme/agent/cto/manifest/v1`.

Call `recall_instruction(intent)` to load relevant instruction sections before
performing any non-trivial task.
```

The body section MUST be no longer than **500 tokens** as measured by a cl100k-compatible tokenizer. Implementations SHOULD target ≤ 450 tokens to leave headroom for adapter injection.

#### §21.1.3 Adapter Profiles {#section-21-1-3}

<div className="stigmem-fields">

<div>
<dt>Profile</dt>
<dt><span className="stigmem-fields__type">Injection</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>paperclip-claude-code</code></dt>
<dt><span className="stigmem-fields__type">Paperclip</span></dt>
<dd>Injects Paperclip tool definitions and heartbeat harness context.</dd>
</div>

<div>
<dt><code>openai-assistants</code></dt>
<dt><span className="stigmem-fields__type">OpenAI</span></dt>
<dd>Injects OpenAI Assistants tool-call shim.</dd>
</div>

<div>
<dt><code>generic</code></dt>
<dt><span className="stigmem-fields__type">none</span></dt>
<dd>Stub is delivered as-is.</dd>
</div>

</div>

Implementations MAY define additional profiles. Unknown profiles MUST be treated as `generic`.

#### §21.1.4 Boot Stub Delivery {#section-21-1-4}

```
GET /v1/agents/{agent_id}/boot-stub[?profile={adapter_profile}]
```

See §21.8.1 for the full wire contract. The boot stub MUST be regenerated whenever the agent's `manifest_uri` changes or the stub schema version increments; stale delivery is a correctness defect, not a warning.

#### §21.1.5 Task-Type Preloads {#section-21-1-5}

Immediately after boot stub delivery and before the agent receives any task context, the runtime MUST deliver the content of all manifest units whose `required_by_task_types` array contains the current heartbeat's wake reason. This is called **task-type preloading**. No retrieval scoring is applied; units are fetched deterministically.

<div className="stigmem-keypoint">

**(S1) Wake reason MUST be sourced from the authenticated heartbeat trigger event.**

E.g. the control-plane JWT or signed adapter payload. The runtime
MUST NOT accept an unverified `wake_reason` claim originating from
the agent's task context or any caller-supplied payload.

</div>

<ol className="stigmem-steps">
<li>Compare the current wake reason against each manifest entry's <code>required_by_task_types</code> array. String comparison is exact and case-sensitive.</li>
<li>All matching units MUST be fetched and injected into the agent's context before any task context is provided.</li>
<li>Preloaded units MUST be included in the heartbeat's audit record under <code>loaded_chunks</code>, tagged with <code>"source": "task_type_preload"</code>.</li>
<li>If a preloaded unit's <code>fact_uri</code> is unreachable, fall back to <code>path</code> if present (<code>"source": "fallback_path"</code>) or surface a <code>preload_unit_unavailable</code> warning and continue. <strong>(S2)</strong> If the unavailable unit has <code>guarantee_load: true</code>, the runtime MUST treat unavailability as fatal and MUST abort the heartbeat. In all cases the warning or error MUST be written to <code>instruction_audit</code>.</li>
<li>Token budget: boot stub + task-type preloads SHOULD remain under 2000 tokens. SHOULD emit <code>preload_budget_warning</code> when exceeded but MUST NOT silently drop units.</li>
</ol>

**Governance:**

<div className="stigmem-grid">

<div><h4>2-task-type cap</h4><p>Any entry with more than 2 <code>required_by_task_types</code> values MUST require explicit admin approval (<code>task_types_approval_required</code>).</p></div>
<div><h4>Enum validation</h4><p>Build pipelines MUST validate strings against the registered wake-reason enum; unknown values MUST cause <code>task_type_unknown</code>.</p></div>
<div><h4>Structural only</h4><p>The intent of task-type preloads is for structurally-predictable critical units. MUST NOT use as a shortcut to load content that should be retrieved semantically.</p></div>
<div><h4>(S3) Blast radius</h4><p>Units in <code>required_by_task_types</code> are exposed unconditionally to all subsequent task context, including adversarial prompt injections later in the same heartbeat. Authors SHOULD NOT declare units containing content that must remain confidential.</p></div>

</div>

---

### §21.2 Instruction Manifest {#section-21-2}

#### §21.2.1 Token Budget {#section-21-2-1}

<div className="stigmem-keypoint">

**The instruction manifest MUST fit within 1000 tokens (cl100k).**

Implementations MUST enforce this at write time and MUST reject a
manifest update that would exceed it with error `manifest_too_large`.

</div>

#### §21.2.2 Manifest Entry Shape {#section-21-2-2}

```json
{
  "name":                   "security-posture",
  "description":            "Security constraints, escalation thresholds, and hard prohibitions.",
  "required_by_task_types": ["issue_assigned", "issue_commented"],
  "guarantee_load":         false,
  "load_triggers": {
    "intents":    ["security rule", "what am I not allowed to do", "escalation threshold"],
    "keywords":   ["security", "escalate", "prohibited", "never"],
    "task_types": ["issue_assigned", "issue_commented", "routine_fired"]
  },
  "fact_uri":       "instruction:acme/agent/cto/security-posture/v2",
  "path":           null,
  "token_estimate": 320
}
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Requirement</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>name</code></dt>
<dt><span className="stigmem-fields__type">MUST · unique</span></dt>
<dd>Stable identifier; unique within the manifest.</dd>
</div>

<div>
<dt><code>description</code></dt>
<dt><span className="stigmem-fields__type">MUST · ≤120 chars</span></dt>
<dd>One-line description of what this unit covers.</dd>
</div>

<div>
<dt><code>required_by_task_types</code></dt>
<dt><span className="stigmem-fields__type">SHOULD for critical units</span></dt>
<dd>Wake-reason strings that cause deterministic preload (§21.1.5).</dd>
</div>

<div>
<dt><code>guarantee_load</code></dt>
<dt><span className="stigmem-fields__type">MAY · max 5/agent</span></dt>
<dd>If true, unit is always appended to <code>recall_instruction</code> responses; requires admin approval; content MUST be safe for any authorised recall caller to observe.</dd>
</div>

<div>
<dt><code>load_triggers.intents</code></dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Natural-language intent phrases.</dd>
</div>

<div>
<dt><code>load_triggers.keywords</code></dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Exact or prefix-match keywords; MAY use BM25 matching.</dd>
</div>

<div>
<dt><code>load_triggers.task_types</code></dt>
<dt><span className="stigmem-fields__type">MAY · semantic hint</span></dt>
<dd>Distinct from <code>required_by_task_types</code>: hint, not deterministic preload.</dd>
</div>

<div>
<dt><code>fact_uri</code> / <code>path</code></dt>
<dt><span className="stigmem-fields__type">exactly one</span></dt>
<dd><code>instruction:</code>-scope stigmem fact URI OR file path. Neither/both → <code>manifest_entry_invalid</code>.</dd>
</div>

<div>
<dt><code>token_estimate</code></dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Used for budget planning.</dd>
</div>

</div>

> **`required_by_task_types` vs `load_triggers.task_types`:** complementary. `required_by_task_types` is a deterministic preload commitment. `load_triggers.task_types` is a semantic hint — it does not guarantee loading.

#### §21.2.3 Manifest Wire Contract {#section-21-2-3}

The manifest is stored as a stigmem fact under the `instruction:` scope (§21.4) and is also surfaced as a structured API resource. See §21.8.2 and §21.8.3.

---

### §21.3 `recall_instruction` Tool Contract {#section-21-3}

#### §21.3.1 Request Shape {#section-21-3-1}

```json
{
  "intent":        "I need to check out an issue and start work",
  "max_chunks":    3,
  "token_budget":  1200,
  "manifest_hint": ["heartbeat-procedure", "checkout-procedure"]
}
```

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required · Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>intent</code></dt>
<dt><span className="stigmem-fields__type">MUST · —</span></dt>
<dd>Free-text description of what the agent is about to do.</dd>
</div>

<div>
<dt><code>max_chunks</code></dt>
<dt><span className="stigmem-fields__type">SHOULD · 3</span></dt>
<dd>Maximum number of instruction units to return.</dd>
</div>

<div>
<dt><code>token_budget</code></dt>
<dt><span className="stigmem-fields__type">SHOULD · 2000</span></dt>
<dd>Soft token budget for the combined response content.</dd>
</div>

<div>
<dt><code>manifest_hint</code></dt>
<dt><span className="stigmem-fields__type">MAY</span></dt>
<dd>Explicit unit names from the manifest; loaded first before ranked retrieval.</dd>
</div>

</div>

#### §21.3.2 Response Shape {#section-21-3-2}

```json
{
  "chunks": [
    {
      "name":        "heartbeat-procedure",
      "fact_uri":    "instruction:acme/agent/cto/heartbeat-procedure/v3",
      "content":     "## Heartbeat Procedure\n\n...",
      "tokens":      420,
      "valid_until": "2027-05-04T00:00:00Z",
      "version":     "v3",
      "score":       0.91,
      "source":      "stigmem"
    }
  ],
  "total_tokens":  420,
  "truncated":     false,
  "missed_hints":  [],
  "audit_token":   "audi_01J..."
}
```

<div className="stigmem-keypoint">

**`audit_token` is a first-class body field, not a header.**

The agent must pass it back when submitting usage feedback. Embedding
it in the body ensures it cannot be silently dropped by middleware.

</div>

`chunks[].source` is `"stigmem"` or `"fallback_path"`. `missed_hints` lists `manifest_hint` names that were not found.

#### §21.3.3 Backing Implementation {#section-21-3-3}

`recall_instruction` MUST be implemented as a stigmem `recall` call restricted to the `instruction:` scope:

```json
POST /v1/recall
{
  "scope":              "instruction:{deployment}/{agent_id}",
  "intent":             "{agent-provided intent string}",
  "max_facts":          "{max_chunks}",
  "token_budget":       "{token_budget}",
  "weights":            { "lexical": 0.35, "semantic": 0.50, "graph": 0.15 },
  "require_garden_ids": ["{agent_instruction_garden_id}"]
}
```

The `require_garden_ids` constraint MUST be applied so that `recall_instruction` cannot return facts from gardens the agent is not authorized to read. If `manifest_hint` is provided, the named units MUST be included before ranked retrieval; missing/inaccessible hints are silently omitted and named in `missed_hints`.

**Guaranteed units (`guarantee_load: true`):**

<ol className="stigmem-steps">
<li><strong>Position.</strong> Guaranteed units MUST be appended after ranked results by default (attention primacy). A unit with <code>force_position: "prepend"</code> MUST be prepended. <strong>(S6)</strong> <code>force_position: "prepend"</code> MUST undergo explicit content review at publish time, recorded in provenance, and MUST require a distinct admin approval record separate from the general <code>guarantee_load</code> approval.</li>
<li><strong>Budget precedence.</strong> Guaranteed units MUST NOT be silently dropped by <code>token_budget</code> exhaustion. Ranked results are truncated first; guaranteed units never to zero.</li>
<li><strong>(S4) Agent cap.</strong> At most 5 manifest units <strong>per agent</strong> may have <code>guarantee_load: true</code>. Publish MUST be rejected with <code>guarantee_cap_exceeded</code> if exceeded.</li>
<li><strong>Relevance threshold.</strong> SHOULD warn if a guaranteed unit has empirical <code>P(relevant | recall_invoked) &lt; 0.6</code>.</li>
<li><strong>Governance.</strong> Requires explicit administrator approval recorded in provenance metadata.</li>
<li><strong>(S5) Confidentiality note.</strong> Guaranteed units are accessible to any principal authorised to invoke <code>recall_instruction</code> for this agent, including via prompt injection. Content in guaranteed units MUST NOT rely on retrieval difficulty for confidentiality.</li>
</ol>

#### §21.3.4 Determinism and Auditability {#section-21-3-4}

<div className="stigmem-keypoint">

**The same `(intent, manifest_hint, max_chunks, token_budget)` tuple MUST produce the same ordered result.**

Given the same set of instruction facts at the same `valid_until`
boundaries. This determinism property enables replay-based audit.

</div>

Implementations MUST record every `recall_instruction` invocation in the discovery audit table before returning. Audit-write failure is logged as `audit_write_failed` but MUST NOT block the response (audit is best-effort).

---

### §21.4 `instruction:` Scope Semantics {#section-21-4}

The `instruction:` URI scheme is a reserved stigmem scope for agent instruction artifacts. It extends §17 (Memory Garden) and §19 (Federation Trust) with instruction-specific semantics.

#### §21.4.1 Scope Namespace {#section-21-4-1}

```
instruction:{deployment}/{agent_id}/{unit_name}/{version}
```

<div className="stigmem-fields">

<div>
<dt>Segment</dt>
<dt><span className="stigmem-fields__type">Constraint</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>&#123;deployment&#125;</code></dt>
<dt><span className="stigmem-fields__type">org root</span></dt>
<dd>MUST match the <code>entity_uri</code> root in the org manifest.</dd>
</div>

<div>
<dt><code>&#123;agent_id&#125;</code></dt>
<dt><span className="stigmem-fields__type">UUID or shortname</span></dt>
<dd>Stable agent UUID or a well-known shortname (e.g. <code>cto</code>).</dd>
</div>

<div>
<dt><code>&#123;unit_name&#125;</code></dt>
<dt><span className="stigmem-fields__type">manifest entry</span></dt>
<dd>The instruction unit name from the manifest.</dd>
</div>

<div>
<dt><code>&#123;version&#125;</code></dt>
<dt><span className="stigmem-fields__type">monotonic</span></dt>
<dd>e.g. <code>v1</code>, <code>v3</code>; MUST be monotonically incrementing; MUST NOT be a floating alias like <code>latest</code>.</dd>
</div>

</div>

The special URI `instruction:{deployment}/{agent_id}/manifest/{version}` addresses the agent's instruction manifest itself.

#### §21.4.2 Versioning {#section-21-4-2}

<div className="stigmem-keypoint">

**Instruction facts are mutable as a series; individual versioned facts are immutable once written.**

A new version MUST be written as a new fact rather than mutating an
existing fact. The previous version's `valid_until` MUST be set to
the new version's `created_at` within the same transaction or a
30-second grace window.

</div>

<div className="stigmem-grid">

<div><h4>Latest version wins</h4><p><code>recall_instruction</code> MUST return only the latest version (highest version string by semantic version ordering).</p></div>
<div><h4>Per-heartbeat cache</h4><p>Agents MAY cache instruction chunks for the duration of a heartbeat/session.</p></div>
<div><h4>No cross-heartbeat cache</h4><p>Unless <code>valid_until</code> extends past the next expected heartbeat time.</p></div>

</div>

#### §21.4.3 Provenance {#section-21-4-3}

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Requirement</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>source_trust</code></dt>
<dt><span className="stigmem-fields__type">MUST · ≥0.9 if human</span></dt>
<dd>Instruction facts authored by verified human administrators SHOULD have <code>source_trust ≥ 0.9</code>.</dd>
</div>

<div>
<dt><code>attestation_chain</code></dt>
<dt><span className="stigmem-fields__type">MUST</span></dt>
<dd>At least one signature from an org manifest key. Unsigned instruction facts MUST be quarantined.</dd>
</div>

<div>
<dt><code>derived_from</code></dt>
<dt><span className="stigmem-fields__type">SHOULD</span></dt>
<dd>Reference the prior version hash when updating; <code>null</code> valid for first version.</dd>
</div>

<div>
<dt><code>authored_by</code></dt>
<dt><span className="stigmem-fields__type">MUST</span></dt>
<dd><code>entity_uri</code> of the human or system that created this version.</dd>
</div>

<div>
<dt><code>authored_at</code></dt>
<dt><span className="stigmem-fields__type">MUST</span></dt>
<dd>ISO 8601 timestamp.</dd>
</div>

</div>

#### §21.4.4 Garden Membership {#section-21-4-4}

All instruction facts MUST be placed in a dedicated instruction garden:

```
garden_id: "instruction:{deployment}:{agent_id}"
```

<div className="stigmem-grid">

<div><h4>Agent: read-only</h4><p>The agent itself, via capability token with verb <code>read</code>.</p></div>
<div><h4>Admins: read + write</h4><p>Via admin API key.</p></div>
<div><h4>Peer agents: no access</h4><p>MUST NOT have read access to another agent's instruction garden unless explicitly granted.</p></div>

</div>

#### §21.4.5 Cross-Agent Confidentiality {#section-21-4-5}

<div className="stigmem-keypoint">

**Cross-agent instruction access is a confidentiality boundary.**

Capability tokens granting `read` on another agent's instruction
scope MUST NOT be derivable unless the requesting agent's role is a
declared supervisor in the org manifest. Federation MUST NOT
replicate instruction-scope facts to peer nodes unless the receiving
node is in the same deployment trust domain. Cross-agent recall
attempts MUST return `403 instruction_scope_denied`. Audit logs MUST
NOT be surfaced to peer agents.

</div>

---

### §21.5 Discovery Audit {#section-21-5}

#### §21.5.1 Audit Record Shape {#section-21-5-1}

```json
{
  "id":            "audevent_01J...",
  "agent_id":      "8e0ed057-bcd8-4f8f-92ee-c046c55b64e9",
  "heartbeat_id":  "run_ad74de74...",
  "session_start": "2026-05-04T12:00:00Z",
  "intent":        "I need to check out an issue and start work",
  "loaded_chunks": ["heartbeat-procedure", "checkout-procedure"],
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": [],
  "audit_token":   "audi_01J...",
  "audit_closed":  "2026-05-04T12:01:05Z",
  "created_at":    "2026-05-04T12:00:02Z"
}
```

The four-way comparison (`intent` → `loaded_chunks` → `used_chunks` → `missed_chunks`) is the raw input for the evaluation metrics defined in §21.5.3. `used_chunks` and `missed_chunks` MAY be populated by the runtime or by the agent via self-report at heartbeat end.

#### §21.5.2 Audit Submission API {#section-21-5-2}

```
POST /v1/instruction/audit
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "audit_token":   "audi_01J...",
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": []
}
→ 204 No Content on success
→ 400 audit_token_invalid  if token not recognized or already fully closed
→ 400 audit_token_expired  if token is older than 24 hours
```

<div className="stigmem-keypoint">

**The audit endpoint MUST be idempotent.**

A second submission with the same `audit_token` MUST return `204`
without modifying the record.

</div>

#### §21.5.3 Replay-Based Evaluation {#section-21-5-3}

<div className="stigmem-fields">

<div>
<dt>Metric</dt>
<dt><span className="stigmem-fields__type">Formula</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt>Recall@k</dt>
<dt><span className="stigmem-fields__type">|used ∩ loaded@k| / |used|</span></dt>
<dd>Fraction of <code>used_chunks</code> that appear in <code>loaded_chunks</code> within rank k.</dd>
</div>

<div>
<dt>Hit@k</dt>
<dt><span className="stigmem-fields__type">≥1 in loaded@k</span></dt>
<dd>Fraction of heartbeats where at least one <code>used_chunk</code> was in <code>loaded_chunks</code>.</dd>
</div>

<div>
<dt>Miss rate</dt>
<dt><span className="stigmem-fields__type">|missed| / (|used| + |missed|)</span></dt>
<dd>Alert when <code>miss_rate &gt; 0.15</code> over 100+ events.</dd>
</div>

</div>

These metrics SHOULD be computed over a rolling 7-day window. Determinism (§21.3.4) guarantees the replay is reproducible.

> **Known limitation — endogeneity of `used_chunks` (non-normative):** All three metrics are computed relative to `used_chunks`, which is itself derived from agent behavior during the heartbeat being measured. An agent that chronically fails to load a required instruction unit will never reference it, so the unit will never appear in `used_chunks`. The chronic miss is therefore invisible to all three live-audit metrics. This is an accepted limitation.
>
> #### 21.5.4 Probe-Set Eval (follow-on, non-normative)
>
> To complement the endogenous live-audit metrics with an exogenous coverage signal, implementations SHOULD maintain a **probe set**: a curated list of `(intent, required_units)` pairs administered independently of the live agent. After every manifest update and on a periodic schedule (e.g. daily), run `recall_instruction(intent)` against each probe and compute Probe-coverage@k and Probe-hit@k.
>
> #### 21.5.5 Probe-Set Coverage Sampling with Soft Score Lift (non-normative)
>
> 1. **Probe-set construction** at manifest publish time. 2. **Background coverage audit** runs daily and on every embedding-model version bump. 3. **Soft score lift** for coverage-critical units: `score += log(1 + λ)` where λ ≈ 0.15. 4. **Coverage endpoint** (§21.8.6). 5. **Probe-set calibration** with PII-stripped real heartbeat intents on a weekly cadence.

---

### §21.6 Migration Semantics {#section-21-6}

#### §21.6.1 Co-existence Period {#section-21-6-1}

<ol className="stigmem-steps">
<li>If a manifest entry has both <code>fact_uri</code> and <code>path</code>, <code>fact_uri</code> MUST take precedence.</li>
<li>If <code>fact_uri</code> lookup fails, the runtime MUST fall back to <code>path</code> if present and MUST append <code>"source": "fallback_path"</code>.</li>
<li>File-path entries are read-only.</li>
<li>The boot stub MUST indicate migration state via <code>migration_mode</code>: <code>"file"</code>, <code>"coexistence"</code>, or <code>"stigmem"</code>.</li>
</ol>

#### §21.6.2 Deprecation Path {#section-21-6-2}

<div className="stigmem-fields">

<div>
<dt>Stage</dt>
<dt><span className="stigmem-fields__type">Mode</span></dt>
<dd>Action</dd>
</div>

<div>
<dt>1. Seed</dt>
<dt><span className="stigmem-fields__type">verify ≥5 heartbeats</span></dt>
<dd>Write instruction content to stigmem as <code>instruction:</code> facts; verify recall quality.</dd>
</div>

<div>
<dt>2. Coexist</dt>
<dt><span className="stigmem-fields__type">coexistence</span></dt>
<dd>Add <code>fact_uri</code> alongside existing <code>path</code>.</dd>
</div>

<div>
<dt>3. Verify</dt>
<dt><span className="stigmem-fields__type">7-day window</span></dt>
<dd>Monitor audit metrics; confirm <code>miss_rate &lt; 0.10</code>.</dd>
</div>

<div>
<dt>4. Promote</dt>
<dt><span className="stigmem-fields__type">stigmem</span></dt>
<dd>Remove <code>path</code> from the manifest entry.</dd>
</div>

<div>
<dt>5. Archive</dt>
<dt><span className="stigmem-fields__type">legacy folder</span></dt>
<dd>Move source markdown to <code>docs/legacy-instructions/</code> with a redirect comment.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Deployments MUST NOT skip Stage 3 (Verify) for agents that handle sensitive operational decisions.**

The risk of an undetected miss in a security-relevant instruction
unit is higher than the cost of a 7-day observation window.

</div>

#### §21.6.3 Bulk Migration Tooling {#section-21-6-3}

Implementations SHOULD provide a `stigmem migrate-instructions` CLI that reads existing markdown, splits at H2/H3 boundaries, writes each section as an `instruction:` fact, and emits a manifest entries array for review. It MUST NOT automatically update the manifest or boot stub.

---

### §21.7 Schema Migrations {#section-21-7}

Three tables support the lazy instruction layer:

<div className="stigmem-grid">

<div><h4><code>instruction_manifests</code></h4><p>Versioned snapshots of each agent's manifest. Previous versions retained with <code>superseded_at</code>.</p></div>
<div><h4><code>instruction_audit</code></h4><p>Append-only log backing the discovery audit. One row per <code>recall_instruction</code> invocation.</p></div>
<div><h4><code>boot_stubs</code></h4><p>Caches the rendered boot stub per <code>(agent_id, adapter_profile)</code>. Invalidated on manifest version change.</p></div>

</div>

```sql
CREATE TABLE IF NOT EXISTS instruction_manifests (
    id               TEXT PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    version          TEXT NOT NULL,
    fact_uri         TEXT NOT NULL,
    token_count      INTEGER NOT NULL,
    body             TEXT NOT NULL,
    created_at       INTEGER NOT NULL,
    superseded_at    INTEGER,
    UNIQUE(agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_manifests_agent ON instruction_manifests (agent_id, superseded_at NULLS FIRST);

CREATE TABLE IF NOT EXISTS instruction_audit (
    id               TEXT PRIMARY KEY,
    agent_id         TEXT NOT NULL,
    heartbeat_id     TEXT NOT NULL,
    session_start    INTEGER NOT NULL,
    intent           TEXT NOT NULL,
    loaded_chunks    TEXT NOT NULL,
    used_chunks      TEXT NOT NULL DEFAULT '[]',
    missed_chunks    TEXT NOT NULL DEFAULT '[]',
    audit_token      TEXT NOT NULL UNIQUE,
    audit_closed     INTEGER,
    created_at       INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_agent_session ON instruction_audit (agent_id, session_start DESC);
CREATE INDEX IF NOT EXISTS idx_audit_token         ON instruction_audit (audit_token);

CREATE TABLE IF NOT EXISTS boot_stubs (
    agent_id          TEXT NOT NULL,
    adapter_profile   TEXT NOT NULL DEFAULT 'generic',
    stub_version      INTEGER NOT NULL DEFAULT 1,
    body              TEXT NOT NULL,
    token_count       INTEGER NOT NULL,
    generated_at      INTEGER NOT NULL,
    manifest_version  TEXT NOT NULL,
    PRIMARY KEY (agent_id, adapter_profile)
);
```

---

### §21.8 Wire Format Additions {#section-21-8}

#### §21.8.1 Get Boot Stub (MUST) {#section-21-8-1}

```
GET /v1/agents/{agent_id}/boot-stub[?profile={adapter_profile}]
Authorization: Bearer <agent api-key or admin api-key>

→ 200 Content-Type: text/markdown
      X-Stub-Version: 1
      X-Manifest-Version: v3
      X-Token-Count: 420
      [stub body]

→ 403 if caller is not the agent itself or an admin
→ 404 if agent not found or no stub generated yet
```

If `profile` is absent, MUST default to `generic`. Unknown profiles MUST be treated as `generic`.

#### §21.8.2 Get Instruction Manifest (MUST) {#section-21-8-2}

```
GET /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <agent api-key or admin api-key>

→ 200 {
    "manifest_version": "v3",
    "fact_uri": "instruction:acme/agent/cto/manifest/v3",
    "token_count": 840,
    "entries": [ ...entry objects... ],
    "last_updated_at": "2026-05-04T00:00:00Z"
  }
→ 403 if caller is not the agent itself or an admin
→ 404 if no manifest configured for agent
```

#### §21.8.3 Publish / Replace Instruction Manifest (MUST) {#section-21-8-3}

```
PUT /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "version": "v4",
  "entries": [ ...entry objects... ],
  "skip_coverage_gate": false
}

→ 200 { "fact_uri": "...", "token_count": 910, "coverage_report": [...] }
→ 400 manifest_too_large
→ 400 manifest_entry_invalid
→ 400 manifest_coverage_failure
→ 400 task_type_unknown
→ 400 guarantee_cap_exceeded
→ 400 task_types_approval_required
→ 409 manifest_version_conflict
```

**Augmented manifest coverage gate (Approach A):**

<ol className="stigmem-steps">
<li>For every string in <code>load_triggers.intents</code>, generate N=5 paraphrases using lexically and syntactically diverse augmentation (MUST NOT use the retrieval encoder's own nearest-neighbour space as the sole paraphrase source).</li>
<li>Run <code>recall_instruction(paraphrase)</code> for each generated paraphrase; check whether this unit appears in top-k results (default k=3).</li>
<li>Compute <code>coverage_pct = (paraphrases where unit in top-k) / (total paraphrases)</code>.</li>
<li>If <code>coverage_pct &lt; 0.80</code> for any unit, the entire publish MUST be rejected with <code>manifest_coverage_failure</code>.</li>
</ol>

<div className="stigmem-keypoint">

**(S7) Two-admin co-sign for skip_coverage_gate on guaranteed-unit manifests.**

When `skip_coverage_gate: true` is used on a manifest containing any
`guarantee_load: true` entry, the bypass provenance record MUST
include co-signatures from at least two distinct administrators
(two distinct `authored_by` entity URIs). Single-admin bypass is
permitted only for manifests with no `guarantee_load: true` entries.
**(S10)** Implementations SHOULD automatically schedule
re-certification within 7 days when `skip_coverage_gate: true` is used.

</div>

<div className="stigmem-keypoint">

**(S8) Paraphrase generator data boundary.**

Paraphrase generation input MUST be limited to `load_triggers.intents`
strings only. Instruction fact content MUST NOT be sent to any
external paraphrase generation service. External services MUST be
listed in the deployment's trust manifest with an appropriate DPA.
Implementations SHOULD prefer local, deterministic paraphrase
methods for confidential instruction content.

</div>

**Re-certification:** When the deployment's embedding model version changes, all existing manifests MUST be re-certified through this gate before the new model version is activated for production recall.

This route MUST atomically: (1) run coverage gate, (2) write manifest fact, (3) update `instruction_manifests` table, (4) invalidate boot stub cache.

#### §21.8.4 Recall Instructions (MUST) {#section-21-8-4}

```
POST /v1/agents/{agent_id}/recall-instruction
Authorization: Bearer <agent api-key>
Content-Type: application/json

{ "intent": "...", "max_chunks": 3, "token_budget": 1200, "manifest_hint": ["heartbeat-procedure"] }

→ 200 { ...response shape per §21.3.2... }
→ 400 intent_required
→ 403 instruction_scope_denied
→ 404 if agent not found
→ 503 recall_backend_unavailable (retryable)
```

#### §21.8.5 Submit Discovery Audit (SHOULD) {#section-21-8-5}

The wire-level route for §21.5.2. This is a SHOULD (not MUST) because the audit is best-effort.

#### §21.8.6 Get Manifest Coverage Report (SHOULD) {#section-21-8-6}

```
GET /v1/agents/{agent_id}/instruction-manifest/coverage
Authorization: Bearer <agent api-key or admin api-key>

Agent-key response:
→ 200 {
    "manifest_version": "v4",
    "embedding_model_version": "nomic-embed-text-v1.5",
    "evaluated_at": "2026-05-04T06:00:00Z",
    "units": [ { "name": "...", "coverage_pct": 0.95, "hit_at_10": 0.92, "probe_count": 20, "last_evaluated_at": "..." } ]
  }

Admin-key response: same as above, plus "coverage_status" field per unit.

→ 403 instruction_scope_denied
→ 404 if no manifest or no coverage report generated yet
```

<div className="stigmem-keypoint">

**(S9) Scope validation + (S11) Categorical label restriction.**

The `agent_id` path parameter MUST be validated against the caller's
API key scope; peer-agent queries MUST return `403`. The
`coverage_status` categorical label (`"ok"`, `"coverage_critical"`,
`"not_evaluated"`) SHOULD be returned only in admin-key responses.
Agent-key responses SHOULD return only raw `coverage_pct` and
`hit_at_10` values, omitting the categorical label — this limits the
retrieval-quality oracle surface for non-admin callers.

</div>

`coverage_status` values (admin-only): `"ok"` (hit@10 ≥ 0.4), `"coverage_critical"` (hit@10 < 0.4, soft-lift eligible), `"not_evaluated"` (probe run not yet completed).

---

### §21.9 Error Reference {#section-21-9}

<div className="stigmem-fields">

<div>
<dt>HTTP</dt>
<dt><span className="stigmem-fields__type">Error code</span></dt>
<dd>Condition</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>intent_required</code></span></dt>
<dd><code>intent</code> field absent or empty.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>manifest_too_large</code></span></dt>
<dd>Manifest exceeds 1000-token budget.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>manifest_entry_invalid</code></span></dt>
<dd>Entry has neither <code>fact_uri</code> nor <code>path</code>, or has both.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>manifest_coverage_failure</code></span></dt>
<dd>One or more units failed the paraphrase coverage gate.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>task_type_unknown</code></span></dt>
<dd><code>required_by_task_types</code> value not in registered enum.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>guarantee_cap_exceeded</code></span></dt>
<dd>More than 5 entries have <code>guarantee_load: true</code>.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>task_types_approval_required</code></span></dt>
<dd>Entry declares &gt; 2 <code>required_by_task_types</code> without admin approval.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>audit_token_invalid</code></span></dt>
<dd>Token not recognized or already fully closed.</dd>
</div>

<div>
<dt>400</dt>
<dt><span className="stigmem-fields__type"><code>audit_token_expired</code></span></dt>
<dd>Token older than 24 hours.</dd>
</div>

<div>
<dt>403</dt>
<dt><span className="stigmem-fields__type"><code>instruction_scope_denied</code></span></dt>
<dd>Caller's token scope does not match the agent's instruction garden.</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type"><code>manifest_not_found</code></span></dt>
<dd>No instruction manifest configured for the agent.</dd>
</div>

<div>
<dt>404</dt>
<dt><span className="stigmem-fields__type"><code>boot_stub_not_found</code></span></dt>
<dd>No boot stub generated yet.</dd>
</div>

<div>
<dt>409</dt>
<dt><span className="stigmem-fields__type"><code>manifest_version_conflict</code></span></dt>
<dd>Version string already exists; manifest versions are immutable.</dd>
</div>

<div>
<dt>503</dt>
<dt><span className="stigmem-fields__type"><code>recall_backend_unavailable</code></span></dt>
<dd>Stigmem recall backend unreachable; retryable.</dd>
</div>

</div>

---

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §21.5.4 {#section-21-5-4}
