---
title: §12. Adapter ABI
sidebar_label: §12 Adapter ABI
audience: Spec
description: "Stigmem spec section 12 — Minimum contract for platform adapters: env vars, assert/query, source binding."
---

# §12. Adapter ABI {#section-12}

**Status:** Stable

Minimum contract for platform adapters: env vars, assert/query, source binding.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

> **v0.6 status:** Promoted from the v0.6 design window reserved section to normative spec, grounded
> in the three v0.6 adapters shipped: MCP (`stigmem/adapters/mcp/`), Paperclip
> (`stigmem/adapters/paperclip/`), and OpenClaw (`stigmem/adapters/openclaw/`).

### §12.1 Adapter Archetypes {#section-12-1}

The ABI recognizes two adapter archetypes with different startup failure contracts:

**Process-mode adapters** (example: MCP `server.ts`): A standalone process whose
sole purpose is to bridge a platform protocol to Stigmem. The process is useless if
Stigmem is not configured; fast failure is correct behavior.

**Middleware adapters** (examples: Paperclip `hook.sh`, OpenClaw `adapter.py`): Code
that extends an existing agent runtime. Stigmem is optional; the agent MUST continue
operating if Stigmem is unconfigured or unreachable.

### §12.2 Required Environment Variables {#section-12-2}

All adapters MUST honor the following environment variables:

| Variable | Required by | Default | Description |
|---|---|---|---|
| `STIGMEM_URL` | All | — | Base URL of the Stigmem node, e.g. `http://localhost:8765` |
| `STIGMEM_API_KEY` | All (optional) | none | API key; required when `auth=required` |
| `STIGMEM_SOURCE_ENTITY` | Middleware | adapter-specific (e.g. `"agent:openclaw"`, `"agent:unknown"`) | Entity URI used as `source` on all write operations. Adapters SHOULD default to a descriptive identity; `"agent:unknown"` is an acceptable last-resort fallback. |

**Process-mode adapters:** MUST exit with a non-zero status code and a clear error
message to stderr if `STIGMEM_URL` is absent.

**Middleware adapters:** MUST silently skip all Stigmem operations if `STIGMEM_URL`
is absent. MUST NOT modify the agent process exit code.

### §12.3 Boot Handshake Protocol {#section-12-3}

The boot handshake runs once when the adapter initializes. It has two phases:
a node probe and (for middleware adapters) a context pull.

#### §12.3.1 Node probe {#section-12-3-1}

Adapters SHOULD issue `GET /.well-known/stigmem` to verify node reachability on startup.

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

Required fields: `version`, `node_id`, `node_url`, `auth`, `federation`.

If the probe fails or required fields are absent:
- **Process-mode adapters:** MUST log an error to stderr. SHOULD NOT crash — allow
  individual tool invocations to fail with a `StigmemError` rather than killing the process.
- **Middleware adapters:** MUST log a warning to stderr. MUST return an empty
  `BootContext`. MUST NOT crash or alter the agent's exit code.

#### §12.3.2 Context pull (middleware adapters only) {#section-12-3-2}

After a successful node probe, middleware adapters that inject context into the agent
system prompt MUST issue the following queries in order. All queries are non-fatal:
a failed or empty response on any individual query MUST NOT abort the boot sequence.

1. **User entity facts**
   ```
   GET /v1/facts?entity={user_entity}&scope=company&min_confidence=0.7
   ```
   Adapters SHOULD filter the result to relevant relation namespaces (e.g. `preference:`).
   Injecting all relations for the user entity may produce a large or noisy context;
   retaining `preference:*` is the reference behavior.

2. **Project constraints** (one query per project entity; skip if no project entities configured)
   ```
   GET /v1/facts?entity={project_entity}&relation=roadmap:constraint&scope=company&min_confidence=0.7
   ```

3. **Pending handoffs targeting this adapter**
   ```
   GET /v1/facts?relation=intent:handoff_to&scope=company&min_confidence=0.8
   ```
   Filter client-side to facts where `value.v == STIGMEM_SOURCE_ENTITY`.
   For each matching handoff entity, additionally pull:
   ```
   GET /v1/facts?entity={handoff_entity}&relation=intent:context_ref&scope=company
   ```

4. **Recent escalations**
   ```
   GET /v1/facts?relation=intent:escalation&scope=company&min_confidence=0.8&limit=10
   ```

#### §12.3.3 BootContext shape {#section-12-3-3}

```
BootContext {
  facts:   Fact[]   // all successfully retrieved facts; empty list if node unreachable
  summary: string   // markdown-formatted context for system prompt injection (see §12.5)
}
```

`BootContext` is always returned, even on total failure. A failed boot returns
`BootContext { facts: [], summary: "" }`.

### §12.4 Write Surfaces {#section-12-4}

Adapters MUST assert the following facts on the specified lifecycle events.

**Write invariants (apply to all assertions):**
- `confidence` MUST be 1.0 unless a per-surface override is listed below.
- All write calls MUST use fire-and-forget semantics: errors MUST be suppressed; the
  adapter MUST NOT crash the agent on write failure.
- Write failures SHOULD be logged to stderr at warning level.

#### §12.4.1 Paperclip-style lifecycle facts {#section-12-4-1}

For adapters that instrument platform issue/task lifecycle:

| Event | `entity` | `relation` | Value type | Value | `scope` |
|---|---|---|---|---|---|
| Checkout (task claimed) | `issue:{task_id}` | `paperclip:checkout` | `string` | `"in_progress"` | `company` |
| Completion | `issue:{task_id}` | `paperclip:issue_status` | `string` | `"done"` | `company` |
| Blocked | `issue:{task_id}` | `paperclip:issue_status` | `string` | `"blocked"` | `company` |
| Blocked by (optional) | `issue:{task_id}` | `paperclip:blocked_by` | `ref` | `"issue:{blocking_id}"` | `company` |
| Activity ping | `issue:{task_id}` | `paperclip:last_active` | `datetime` | ISO 8601 UTC now | `local` |

**Activity ping scope:** `paperclip:last_active` MUST use `scope="local"`. Activity
pings are heartbeat signals for intra-node observability; they MUST NOT be federated.

**Entity URI format note:** The `entity` column above uses informal URI shorthand
(`issue:{task_id}`). Per §2.5, adapters targeting v0.6+ SHOULD use formal URIs:
`stigmem://{node_authority}/issue/{task_id}`, where `{node_authority}` is the
hostname component of `STIGMEM_URL`. Adapters that do not have access to the
node authority MAY use the informal form — the node will accept it and emit a
deprecation warning to stderr. Migration to formal URIs is tracked for v0.7.

#### §12.4.2 Handoff facts {#section-12-4-2}

Emitted when an agent session ends or delegates to another agent. Mint a synthetic
entity `handoff:{uuid}` and assert all of the following:

| `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|
| `intent:handoff_to` | `ref` | target agent entity URI | 1.0 | `company` |
| `intent:handoff_summary` | `text` | human-readable summary (≤ 4 KB) | 1.0 | `company` |
| `intent:context_ref` | `ref` | fact ID URI for each referenced context fact (one assertion per ref) | 1.0 | `company` |
| `intent:continuation` | `text` | continuation note (optional; omit if absent) | 1.0 | `company` |

`intent:handoff_to` and `intent:handoff_summary` are REQUIRED. `intent:context_ref`
MUST have at least one assertion if `fact_refs` is non-empty. `intent:continuation`
is OPTIONAL.

#### §12.4.3 Decision facts {#section-12-4-3}

Emitted when an agent makes a significant architectural or roadmap choice:

| `entity` | `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|---|
| `{decision_entity}` | `roadmap:decision` | `text` | decision summary (≤ 4 KB) | 1.0 | `company` |

The `{decision_entity}` SHOULD be a formal URI: `stigmem://{node_authority}/decision/{slug}`.

#### §12.4.4 Escalation facts {#section-12-4-4}

Emitted when an agent cannot proceed and must escalate. Mint a synthetic entity
`escalation:{uuid}` and assert:

| `relation` | Value type | Value | `confidence` | `scope` |
|---|---|---|---|---|
| `intent:escalation` | `string` | priority: `"low"` \| `"medium"` \| `"high"` \| `"critical"` | 1.0 | `company` |
| `intent:escalate_to` | `ref` | target agent or user entity URI | 1.0 | `company` |
| `intent:goal` | `text` | goal statement describing what the agent could not complete (≤ 2 KB) | 1.0 | `company` |

All three assertions are REQUIRED for a complete escalation record.

#### §12.4.5 Minimum confidence and scope requirements summary {#section-12-4-5}

| Fact class | Min confidence | Required scope |
|---|---|---|
| Lifecycle status (`paperclip:checkout`, `paperclip:issue_status`, `paperclip:blocked_by`) | 1.0 | `company` |
| Activity ping (`paperclip:last_active`) | 1.0 | `local` (never federated) |
| Handoff facts | 1.0 | `company` |
| Decision facts | 1.0 | `company` |
| Escalation facts | 1.0 | `company` |

Adapters MUST NOT write lifecycle or intent facts with confidence below 1.0. Low-confidence
writes on these relations would pollute conflict resolution and break downstream agents
that depend on these facts for routing.

### §12.5 Context Injection Format {#section-12-5}

Adapters that inject Stigmem facts into an agent's system prompt MUST use the
following markdown schema:

```markdown
## Stigmem context — {user_entity}

### {namespace}
- **{relation}** on `{entity}`: {value_str}[ _(confidence: {confidence:.2f})_]
```

**Field rendering rules:**
- `{user_entity}`: the primary entity passed to the boot handshake
- `{namespace}`: the relation prefix before the first `:` (e.g. `preference`, `roadmap`);
  facts with the same namespace are grouped under a shared `### {namespace}` subheading
- `{relation}`: the fact's `relation` field, verbatim
- `{entity}`: the fact's `entity` field, verbatim
- `{value_str}`: for `null` type → render `(null)`; for all other types → render `value.v` as a string
- Confidence annotation: rendered only when `confidence < 1.0`, using the format
  `_(confidence: {value:.2f})_`. Facts with `confidence == 1.0` omit the annotation.

**Ordering:** Facts SHOULD be ordered by descending `confidence`, then descending `hlc` within equal confidence.

**Empty context:** If no facts were retrieved, adapters MUST return an empty string
and MUST NOT inject the `## Stigmem context` header. Do not inject a header with
zero fact lines.

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

### §12.6 Error Handling Contract {#section-12-6}

The crash-forbidden invariant: **under no circumstances MAY a Stigmem adapter crash
the host agent process due to a Stigmem node failure.** The adapter is middleware;
the agent's core functionality MUST remain unaffected if Stigmem is degraded or absent.

| Scenario | Process-mode adapter | Middleware adapter |
|---|---|---|
| `STIGMEM_URL` absent | Exit non-zero with clear error to stderr | Skip all Stigmem ops silently; exit 0 |
| Node unreachable at boot | Log error to stderr; continue (let tool calls fail individually) | Log warning to stderr; return `BootContext { facts:[], summary:"" }`; continue |
| Node unreachable on write | Log warning to stderr; no crash | Log warning to stderr; no crash |
| Node returns HTTP 4xx on write | Log error to stderr; no retry; no crash | Log error to stderr; no retry; no crash |
| Node returns HTTP 5xx on write | Log error to stderr; retry once after 2 s; suppress on second failure | Log error to stderr; retry once after 2 s; suppress on second failure |
| Boot query returns HTTP 4xx | Treat as empty result for that query | Treat as empty result for that query |
| Boot query returns HTTP 5xx | Treat as empty result; log warning | Treat as empty result; log warning |
| Node unreachable on tool invocation (MCP) | Return `isError: true` with error text in tool result; do not exit | N/A |

### §12.7 Conformance Test Vectors {#section-12-7}

A compliant adapter MUST pass all vectors defined in:

```
sdks/stigmem-py/tests/conformance_vectors.py
```

The vectors are JSON-serialisable dicts shared across the Python and TypeScript SDKs.

**Vector sets:**

| Set | IDs | What it verifies |
|---|---|---|
| `ASSERT_VECTORS` | `assert-string`, `assert-text`, `assert-ref`, `retract` | `POST /v1/facts` with each FactValue type; `confidence=0.0` retraction |
| `QUERY_VECTORS` | `query-by-entity`, `query-by-entity-relation`, `query-min-confidence`, `query-include-contradicted` | `GET /v1/facts` filtering; required response fields |
| `NODE_INFO_VECTOR` | `node-info` | `GET /.well-known/stigmem` required fields: `version`, `node_id`, `node_url`, `auth`, `federation` |
| `LINT_VECTORS` | `lint-contradiction`, `lint-stale`, `lint-stale-lookahead`, `lint-orphan`, `lint-broken-ref`, `lint-broken-ref-intent`, `lint-clean`, `lint-scope-filter` | `POST /v1/lint` — all four checks; severity mapping; scope isolation |
| `DECAY_VECTORS` | `decay-confidence-reduction`, `decay-retraction`, `decay-scope-filter`, `decay-dry-run`, `decay-exempt` | `POST /v1/decay/sweep` — confidence decay, retraction, scope isolation, dry-run mode, exempt relations |
| `SYNTHESIS_VECTORS` | `synthesis-basic`, `synthesis-contradicted`, `synthesis-min-confidence`, `synthesis-empty` | `POST /v1/synthesis` — confidence ordering, contradiction annotation, min-confidence filter |

**Running conformance:**
```bash
# Python SDK (also runs adapter integration tests)
pytest sdks/stigmem-py/tests/ -v

# TypeScript SDK
cd sdks/stigmem-ts && npm test
```

**Adapter-specific gate:** Adapters that write lifecycle or intent facts (§12.4) MUST
additionally demonstrate correct assertion behavior via an integration test that
verifies:
1. The expected relations are present in the fact store after each lifecycle event.
2. Facts written with the wrong scope or below minimum confidence are rejected before
   reaching the node (validated client-side) or are caught in the node's response.

A compliant adapter is one that passes all `ASSERT_VECTORS`, `QUERY_VECTORS`,
`NODE_INFO_VECTOR`, `LINT_VECTORS`, `DECAY_VECTORS`, `SYNTHESIS_VECTORS`, and its
adapter-specific lifecycle tests with a live Stigmem node.

---
