---
title: Spec-19 Adapter ABI
sidebar_label: Spec-19 Adapter ABI
audience: Spec
description: "Spec-19-Adapter-ABI rendered entry point — minimum adapter contract and conformance expectations."
---

# Spec-19-Adapter-ABI \{#section-12\}

<p className="stigmem-meta"><span>6 min read</span><span>Spec contributor · Adapter author</span><span>Process + middleware contract</span></p>

<div className="stigmem-lead">

**What this page is**

Rendered compatibility entry point for
[`Spec-19-Adapter-ABI`](https://github.com/eidetic-labs/stigmem/blob/main/spec/specs/19-adapter-abi.md).
Minimum contract for platform adapters: env vars, assert/query,
source binding.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source.
:::

<div className="stigmem-keypoint">

**pre-reset status.**

Promoted from the pre-reset design work reserved section to normative
spec, grounded in the three pre-reset adapters shipped: MCP
(<code>stigmem/adapters/mcp/</code>), Paperclip
(<code>stigmem/adapters/paperclip/</code>), and OpenClaw
(<code>stigmem/adapters/openclaw/</code>).

</div>

### §12.1 Adapter archetypes \{#section-12-1\}

The ABI recognizes two adapter archetypes with different startup
failure contracts.

<div className="stigmem-fields">

<div>
<dt>Archetype</dt>
<dt><span className="stigmem-fields__type">Example</span></dt>
<dd>Failure contract</dd>
</div>

<div>
<dt>Process-mode adapter</dt>
<dt><span className="stigmem-fields__type">MCP <code>server.ts</code></span></dt>
<dd>A standalone process whose sole purpose is to bridge a platform protocol to Stigmem. The process is useless if Stigmem is not configured; fast failure is correct behavior.</dd>
</div>

<div>
<dt>Middleware adapter</dt>
<dt><span className="stigmem-fields__type">Paperclip <code>hook.sh</code> · OpenClaw <code>adapter.py</code></span></dt>
<dd>Code that extends an existing agent runtime. Stigmem is optional; the agent MUST continue operating if Stigmem is unconfigured or unreachable.</dd>
</div>

</div>

### §12.2 Required environment variables \{#section-12-2\}

All adapters MUST honor the following environment variables.

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Required by · Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_URL</code></dt>
<dt><span className="stigmem-fields__type">All · —</span></dt>
<dd>Base URL of the Stigmem node, e.g. <code>http://localhost:8765</code>.</dd>
</div>

<div>
<dt><code>STIGMEM_API_KEY</code></dt>
<dt><span className="stigmem-fields__type">All (optional) · none</span></dt>
<dd>API key; required when <code>auth=required</code>.</dd>
</div>

<div>
<dt><code>STIGMEM_SOURCE_ENTITY</code></dt>
<dt><span className="stigmem-fields__type">Middleware · adapter-specific</span></dt>
<dd>Entity URI used as <code>source</code> on all write operations. Adapters SHOULD default to a descriptive identity; <code>"agent:unknown"</code> is an acceptable last-resort fallback.</dd>
</div>

</div>

**Process-mode adapters:** MUST exit with a non-zero status code and
a clear error message to stderr if `STIGMEM_URL` is absent.

**Middleware adapters:** MUST silently skip all Stigmem operations if
`STIGMEM_URL` is absent. MUST NOT modify the agent process exit code.

### §12.3 Boot handshake protocol \{#section-12-3\}

The boot handshake runs once when the adapter initializes. It has
two phases: a node probe and (for middleware adapters) a context pull.

#### §12.3.1 Node probe \{#section-12-3-1\}

Adapters SHOULD issue `GET /.well-known/stigmem` to verify node
reachability on startup.

Expected response shape:

```json
{
  "version":    "0.8",
  "node_id":    "<URI>",
  "node_url":   "<string>",
  "auth":       "none" | "required",
  "federation": "disabled" | "enabled"
}
```

Required fields: `version`, `node_id`, `node_url`, `auth`,
`federation`.

If the probe fails or required fields are absent:

<div className="stigmem-fields">

<div>
<dt>Archetype</dt>
<dt><span className="stigmem-fields__type">On probe failure</span></dt>
<dd>Recovery</dd>
</div>

<div>
<dt>Process-mode</dt>
<dt><span className="stigmem-fields__type">log error to stderr</span></dt>
<dd>SHOULD NOT crash — allow individual tool invocations to fail with a <code>StigmemError</code> rather than killing the process.</dd>
</div>

<div>
<dt>Middleware</dt>
<dt><span className="stigmem-fields__type">log warning to stderr</span></dt>
<dd>MUST return an empty <code>BootContext</code>. MUST NOT crash or alter the agent's exit code.</dd>
</div>

</div>

#### §12.3.2 Context pull (middleware adapters only) \{#section-12-3-2\}

After a successful node probe, middleware adapters that inject
context into the agent system prompt MUST issue the following
queries in order. All queries are non-fatal: a failed or empty
response on any individual query MUST NOT abort the boot sequence.

<ol className="stigmem-steps">
<li><strong>User entity facts.</strong> <code>GET /v1/facts?entity={`{user_entity}`}&scope=company&min_confidence=0.7</code>. Adapters SHOULD filter the result to relevant relation namespaces (e.g. <code>preference:</code>).</li>
<li><strong>Project constraints.</strong> One query per project entity; skip if no project entities configured: <code>GET /v1/facts?entity={`{project_entity}`}&relation=roadmap:constraint&scope=company&min_confidence=0.7</code>.</li>
<li><strong>Pending handoffs targeting this adapter.</strong> <code>GET /v1/facts?relation=intent:handoff_to&scope=company&min_confidence=0.8</code>. Filter client-side to facts where <code>value.v == STIGMEM_SOURCE_ENTITY</code>.</li>
<li><strong>Recent escalations.</strong> <code>GET /v1/facts?relation=intent:escalation&scope=company&min_confidence=0.8&limit=10</code>.</li>
</ol>

#### §12.3.3 BootContext shape \{#section-12-3-3\}

```
BootContext {
  facts:   Fact[]   // all successfully retrieved facts; empty list if node unreachable
  summary: string   // markdown-formatted context for system prompt injection (see §12.5)
}
```

`BootContext` is always returned, even on total failure. A failed
boot returns `BootContext { facts: [], summary: "" }`.

### §12.4 Write surfaces \{#section-12-4\}

Adapters MUST assert the following facts on the specified lifecycle
events.

<div className="stigmem-keypoint">

**Write invariants (apply to all assertions).**

<code>confidence</code> MUST be 1.0 unless a per-surface override is
listed. All write calls MUST use fire-and-forget semantics: errors
MUST be suppressed; the adapter MUST NOT crash the agent on write
failure. Write failures SHOULD be logged to stderr at warning level.

</div>

#### §12.4.1 Paperclip-style lifecycle facts \{#section-12-4-1\}

For adapters that instrument platform issue/task lifecycle.

<div className="stigmem-fields">

<div>
<dt>Event</dt>
<dt><span className="stigmem-fields__type">Relation · Value · Scope</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Checkout (task claimed)</dt>
<dt><span className="stigmem-fields__type"><code>paperclip:checkout</code> · <code>"in_progress"</code> · <code>company</code></span></dt>
<dd>Entity: <code>issue:{`{task_id}`}</code>.</dd>
</div>

<div>
<dt>Completion</dt>
<dt><span className="stigmem-fields__type"><code>paperclip:issue_status</code> · <code>"done"</code> · <code>company</code></span></dt>
<dd></dd>
</div>

<div>
<dt>Blocked</dt>
<dt><span className="stigmem-fields__type"><code>paperclip:issue_status</code> · <code>"blocked"</code> · <code>company</code></span></dt>
<dd></dd>
</div>

<div>
<dt>Blocked by (optional)</dt>
<dt><span className="stigmem-fields__type"><code>paperclip:blocked_by</code> · ref · <code>company</code></span></dt>
<dd>Value: <code>"issue:{`{blocking_id}`}"</code>.</dd>
</div>

<div>
<dt>Activity ping</dt>
<dt><span className="stigmem-fields__type"><code>paperclip:last_active</code> · datetime · <code>local</code></span></dt>
<dd><strong>Activity pings MUST use <code>scope="local"</code></strong> — heartbeat signals for intra-node observability; MUST NOT be federated.</dd>
</div>

</div>

**Entity URI format note:** The `entity` column above uses informal
URI shorthand (`issue:{task_id}`). Per §2.5, adapters targeting
pre-reset+ SHOULD use formal URIs:
`stigmem://{node_authority}/issue/{task_id}`. Migration tracked for
pre-reset.

#### §12.4.2 Handoff facts \{#section-12-4-2\}

Emitted when an agent session ends or delegates to another agent.
Mint a synthetic entity `handoff:{uuid}` and assert all of the
following.

<div className="stigmem-fields">

<div>
<dt>Relation</dt>
<dt><span className="stigmem-fields__type">Type · Required?</span></dt>
<dd>Value</dd>
</div>

<div>
<dt><code>intent:handoff_to</code></dt>
<dt><span className="stigmem-fields__type">ref · REQUIRED</span></dt>
<dd>Target agent entity URI.</dd>
</div>

<div>
<dt><code>intent:handoff_summary</code></dt>
<dt><span className="stigmem-fields__type">text · REQUIRED</span></dt>
<dd>Human-readable summary (≤ 4 KB).</dd>
</div>

<div>
<dt><code>intent:context_ref</code></dt>
<dt><span className="stigmem-fields__type">ref · ≥1 if <code>fact_refs</code> non-empty</span></dt>
<dd>Fact ID URI per referenced context fact (one assertion per ref).</dd>
</div>

<div>
<dt><code>intent:continuation</code></dt>
<dt><span className="stigmem-fields__type">text · OPTIONAL</span></dt>
<dd>Continuation note; omit if absent.</dd>
</div>

</div>

All `confidence` 1.0, `scope` `company`.

#### §12.4.3 Decision facts \{#section-12-4-3\}

Emitted when an agent makes a significant architectural or roadmap
choice.

<div className="stigmem-fields">

<div>
<dt>Entity</dt>
<dt><span className="stigmem-fields__type">Relation · Type · Value</span></dt>
<dd>Scope · confidence</dd>
</div>

<div>
<dt><code>{`{decision_entity}`}</code></dt>
<dt><span className="stigmem-fields__type"><code>roadmap:decision</code> · text · summary (≤4 KB)</span></dt>
<dd><code>company</code> · 1.0</dd>
</div>

</div>

The `{decision_entity}` SHOULD be a formal URI:
`stigmem://{node_authority}/decision/{slug}`.

#### §12.4.4 Escalation facts \{#section-12-4-4\}

Emitted when an agent cannot proceed and must escalate. Mint a
synthetic entity `escalation:{uuid}` and assert all three.

<div className="stigmem-fields">

<div>
<dt>Relation</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Value (all REQUIRED)</dd>
</div>

<div>
<dt><code>intent:escalation</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Priority: <code>"low"</code> | <code>"medium"</code> | <code>"high"</code> | <code>"critical"</code>.</dd>
</div>

<div>
<dt><code>intent:escalate_to</code></dt>
<dt><span className="stigmem-fields__type">ref</span></dt>
<dd>Target agent or user entity URI.</dd>
</div>

<div>
<dt><code>intent:goal</code></dt>
<dt><span className="stigmem-fields__type">text</span></dt>
<dd>Goal statement describing what the agent could not complete (≤ 2 KB).</dd>
</div>

</div>

All `confidence` 1.0, `scope` `company`.

#### §12.4.5 Minimum confidence and scope requirements summary \{#section-12-4-5\}

<div className="stigmem-fields">

<div>
<dt>Fact class</dt>
<dt><span className="stigmem-fields__type">Min confidence · Required scope</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Lifecycle status</dt>
<dt><span className="stigmem-fields__type">1.0 · <code>company</code></span></dt>
<dd><code>paperclip:checkout</code>, <code>paperclip:issue_status</code>, <code>paperclip:blocked_by</code>.</dd>
</div>

<div>
<dt>Activity ping</dt>
<dt><span className="stigmem-fields__type">1.0 · <code>local</code> (never federated)</span></dt>
<dd><code>paperclip:last_active</code>.</dd>
</div>

<div>
<dt>Handoff / Decision / Escalation facts</dt>
<dt><span className="stigmem-fields__type">1.0 · <code>company</code></span></dt>
<dd></dd>
</div>

</div>

Adapters MUST NOT write lifecycle or intent facts with confidence
below 1.0. Low-confidence writes on these relations would pollute
conflict resolution and break downstream agents that depend on these
facts for routing.

### §12.5 Context injection format \{#section-12-5\}

Adapters that inject Stigmem facts into an agent's system prompt
MUST use the following markdown schema.

````markdown
## Stigmem context — {user_entity}

### {namespace}
- **{relation}** on `{entity}`: {value_str}[ _(confidence: {confidence:.2f})_]
````

<div className="stigmem-grid">

<div><h4><code>{`{user_entity}`}</code></h4><p>The primary entity passed to the boot handshake.</p></div>
<div><h4><code>{`{namespace}`}</code></h4><p>The relation prefix before the first <code>:</code>; facts grouped under shared <code>### {`{namespace}`}</code>.</p></div>
<div><h4><code>{`{relation}`}</code></h4><p>The fact's <code>relation</code> field, verbatim.</p></div>
<div><h4><code>{`{entity}`}</code></h4><p>The fact's <code>entity</code> field, verbatim.</p></div>
<div><h4><code>{`{value_str}`}</code></h4><p>For <code>null</code> type → render <code>(null)</code>; for others → render <code>value.v</code> as string.</p></div>
<div><h4>Confidence annotation</h4><p>Rendered only when <code>confidence &lt; 1.0</code>, as <code>_(confidence: {`{value:.2f}`})_</code>.</p></div>

</div>

**Ordering:** Facts SHOULD be ordered by descending `confidence`,
then descending `hlc` within equal confidence.

<div className="stigmem-keypoint">

**Empty context.**

If no facts were retrieved, adapters MUST return an empty string and
MUST NOT inject the <code>## Stigmem context</code> header. Do not
inject a header with zero fact lines.

</div>

**Reference implementation** (`stigmem/adapters/openclaw/adapter.py:_facts_to_summary`):

```python
def _facts_to_summary(facts: list[Fact], user_entity: str) -> str:
    if not facts:
        return ""
    groups: dict[str, list[Fact]] = {}
    for fact in facts:
        ns = fact.relation.split(":")[0] if ":" in fact.relation else fact.relation
        groups.setdefault(ns, []).append(fact)
    lines = [f"## Stigmem context — {user_entity}\n"]
    for ns, ns_facts in groups.items():
        lines.append(f"### {ns}")
        for fact in ns_facts:
            val = getattr(fact.value, "v", "(null)") if fact.value is not None else "(null)"
            confidence_note = f" _(confidence: {fact.confidence:.2f})_" if fact.confidence < 1.0 else ""
            lines.append(f"- **{fact.relation}** on `{fact.entity}`: {val}{confidence_note}")
        lines.append("")
    return "\n".join(lines).rstrip()
```

### §12.6 Error handling contract \{#section-12-6\}

<div className="stigmem-keypoint">

**The crash-forbidden invariant.**

Under no circumstances MAY a Stigmem adapter crash the host agent
process due to a Stigmem node failure. The adapter is middleware;
the agent's core functionality MUST remain unaffected if Stigmem is
degraded or absent.

</div>

<div className="stigmem-fields">

<div>
<dt>Scenario</dt>
<dt><span className="stigmem-fields__type">Process-mode</span></dt>
<dd>Middleware</dd>
</div>

<div>
<dt><code>STIGMEM_URL</code> absent</dt>
<dt><span className="stigmem-fields__type">Exit non-zero; clear error to stderr</span></dt>
<dd>Skip all Stigmem ops silently; exit 0.</dd>
</div>

<div>
<dt>Node unreachable at boot</dt>
<dt><span className="stigmem-fields__type">Log error to stderr; continue (let tool calls fail individually)</span></dt>
<dd>Log warning to stderr; return empty <code>BootContext</code>; continue.</dd>
</div>

<div>
<dt>Node unreachable on write</dt>
<dt><span className="stigmem-fields__type">Log warning; no crash</span></dt>
<dd>Log warning; no crash.</dd>
</div>

<div>
<dt>Node returns HTTP 4xx on write</dt>
<dt><span className="stigmem-fields__type">Log error; no retry; no crash</span></dt>
<dd>Log error; no retry; no crash.</dd>
</div>

<div>
<dt>Node returns HTTP 5xx on write</dt>
<dt><span className="stigmem-fields__type">Log error; retry once after 2s; suppress on second failure</span></dt>
<dd>Same: log error; retry once after 2s; suppress.</dd>
</div>

<div>
<dt>Boot query returns HTTP 4xx</dt>
<dt><span className="stigmem-fields__type">Treat as empty result</span></dt>
<dd>Same.</dd>
</div>

<div>
<dt>Boot query returns HTTP 5xx</dt>
<dt><span className="stigmem-fields__type">Treat as empty result; log warning</span></dt>
<dd>Same.</dd>
</div>

<div>
<dt>Node unreachable on MCP tool</dt>
<dt><span className="stigmem-fields__type">Return <code>isError: true</code> with error text; do not exit</span></dt>
<dd>N/A.</dd>
</div>

</div>

### §12.7 Conformance test vectors \{#section-12-7\}

A compliant adapter MUST pass all vectors defined in:

```
sdks/stigmem-py/tests/conformance_vectors.py
```

The vectors are JSON-serialisable dicts shared across the Python and
TypeScript SDKs.

<div className="stigmem-fields">

<div>
<dt>Set</dt>
<dt><span className="stigmem-fields__type">IDs</span></dt>
<dd>What it verifies</dd>
</div>

<div>
<dt><code>ASSERT_VECTORS</code></dt>
<dt><span className="stigmem-fields__type">assert-string · assert-text · assert-ref · retract</span></dt>
<dd><code>POST /v1/facts</code> with each FactValue type; <code>confidence=0.0</code> retraction.</dd>
</div>

<div>
<dt><code>QUERY_VECTORS</code></dt>
<dt><span className="stigmem-fields__type">query-by-entity · query-by-entity-relation · query-min-confidence · query-include-contradicted</span></dt>
<dd><code>GET /v1/facts</code> filtering; required response fields.</dd>
</div>

<div>
<dt><code>NODE_INFO_VECTOR</code></dt>
<dt><span className="stigmem-fields__type">node-info</span></dt>
<dd><code>GET /.well-known/stigmem</code> required fields.</dd>
</div>

<div>
<dt><code>LINT_VECTORS</code></dt>
<dt><span className="stigmem-fields__type">8 vectors</span></dt>
<dd><code>POST /v1/lint</code> — all four checks; severity mapping; scope isolation.</dd>
</div>

<div>
<dt><code>DECAY_VECTORS</code></dt>
<dt><span className="stigmem-fields__type">5 vectors</span></dt>
<dd><code>POST /v1/decay/sweep</code> — confidence decay, retraction, scope isolation, dry-run mode, exempt relations.</dd>
</div>

<div>
<dt><code>SYNTHESIS_VECTORS</code></dt>
<dt><span className="stigmem-fields__type">4 vectors</span></dt>
<dd><code>POST /v1/synthesis</code> — confidence ordering, contradiction annotation, min-confidence filter.</dd>
</div>

</div>

**Running conformance:**

```bash
# Python SDK (also runs adapter integration tests)
pytest sdks/stigmem-py/tests/ -v

# TypeScript SDK
cd sdks/stigmem-ts && npm test
```

**Adapter-specific gate:** Adapters that write lifecycle or intent
facts (§12.4) MUST additionally demonstrate correct assertion
behavior via an integration test that verifies:

<ol className="stigmem-steps">
<li>The expected relations are present in the fact store after each lifecycle event.</li>
<li>Facts written with the wrong scope or below minimum confidence are rejected before reaching the node (validated client-side) or are caught in the node's response.</li>
</ol>

A compliant adapter is one that passes all `ASSERT_VECTORS`,
`QUERY_VECTORS`, `NODE_INFO_VECTOR`, `LINT_VECTORS`, `DECAY_VECTORS`,
`SYNTHESIS_VECTORS`, and its adapter-specific lifecycle tests with a
live Stigmem node.
