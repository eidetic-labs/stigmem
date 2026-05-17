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

**Status:** Experimental / opt-in source package on `main`

Boot stub + manifest + on-demand recall for token-efficient agent instruction loading.

**Source material:** Archived evolutionary spec snapshots. This page is the maintained Spec-X home for lazy instruction discovery.

:::caution EXPERIMENTAL
The boot-stub schema and instruction-manifest format are not yet finalized and may change in a future minor release. Do not deploy lazy-discovered instructions in production agents handling sensitive data or irreversible tool use until this section reaches GA. Always pin `instructions_manifest_uri` to a trusted, integrity-verified source.
:::

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

**Status:** Experimental. Implementation source is opt-in and remains outside the supported default install.

This section specifies how agents discover and load their instructions on demand rather than preloading every instruction document at startup. The mechanism has three runtime components — a **boot stub**, an **instruction manifest**, and the **`recall_instruction` tool** — and one off-path component, the **discovery audit**, used for continuous retrieval-quality evaluation.

---

### §21.1 Boot Stub {#section-21-1}

The boot stub is the minimal agent preamble loaded unconditionally at the start of every heartbeat or session. Its purpose is to give the agent enough context to function and to provide handles for lazy-loading the rest of its instructions.

#### §21.1.1 Required Content {#section-21-1-1}

A compliant boot stub MUST contain all of the following fields:

| Field | Description |
|---|---|
| `agent_id` | Stable UUID that uniquely identifies this agent within the deployment |
| `agent_role` | Human-readable role label (e.g. `"CTO"`, `"ResearchScientist"`) |
| `heartbeat_contract` | URI or `instruction:` fact URI pointing to the heartbeat procedure document |
| `manifest_uri` | `instruction:` scope URI for the instruction manifest (§21.2) |
| `recall_tool_schema` | Inline JSON Schema for the `recall_instruction` tool (§21.3); MUST be present so the agent can invoke it without a separate fetch |

The boot stub SHOULD NOT contain operational instruction content — instructions SHOULD be loaded lazily via `recall_instruction`. **Exception:** rules that apply unconditionally on every heartbeat regardless of task type (e.g. mandatory escalation thresholds, universal security constraints, hard "never-do" prohibitions) MAY be embedded directly in the boot stub body. This is the primary mitigation against chronic instruction-scope misses (§21.5.3 limitation note): a rule that is always in context cannot be silently missed by a retrieval failure. Deployments SHOULD classify each instruction unit as either "always applicable" (candidate for boot stub embedding) or "task-conditional" (lazy-load via manifest) during the manifest authoring phase.

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
performing any non-trivial task. The manifest lists available sections and their
triggers to help you decide when to load.
```

The body section (after the frontmatter) MUST be no longer than **500 tokens** as measured by a cl100k-compatible tokenizer. Implementations SHOULD target ≤ 450 tokens to leave headroom for adapter injection.

#### §21.1.3 Adapter Profiles {#section-21-1-3}

The `adapter_profile` frontmatter field allows runtimes to inject adapter-specific content (tool declarations, permission banners, etc.) after boot stub delivery. Supported built-in profiles:

| Profile | Description |
|---|---|
| `paperclip-claude-code` | Injects Paperclip tool definitions and heartbeat harness context |
| `openai-assistants` | Injects OpenAI Assistants tool-call shim |
| `generic` | No runtime injection; stub is delivered as-is |

Implementations MAY define additional profiles. Unknown profiles MUST be treated as `generic`.

#### §21.1.4 Boot Stub Delivery {#section-21-1-4}

The boot stub for an agent MUST be retrievable via:

```
GET /v1/agents/{agent_id}/boot-stub[?profile={adapter_profile}]
```

See §21.8.1 for the full wire contract. The boot stub MUST be regenerated whenever the agent's `manifest_uri` changes or the stub schema version increments; stale delivery is a correctness defect, not a warning.

#### §21.1.5 Task-Type Preloads {#section-21-1-5}

Immediately after boot stub delivery and before the agent receives any task context, the runtime MUST deliver the content of all manifest units whose `required_by_task_types` array contains the current heartbeat's wake reason. This is called **task-type preloading**. No retrieval scoring is applied; units are fetched deterministically.

Rules:

1. The runtime MUST compare the current wake reason against each manifest entry's `required_by_task_types` array. String comparison is exact and case-sensitive. **The wake reason MUST be sourced from the authenticated heartbeat trigger event (e.g. the control-plane JWT or signed adapter payload). The runtime MUST NOT accept an unverified `wake_reason` claim originating from the agent's task context or any caller-supplied payload when dispatching preloads.** (S1)
2. All matching units MUST be fetched and injected into the agent's context before any task context is provided.
3. Preloaded units MUST be included in the heartbeat's audit record under `loaded_chunks`, tagged with `"source": "task_type_preload"`.
4. If a preloaded unit's `fact_uri` is unreachable, the runtime MUST fall back to `path` if present (with `"source": "fallback_path"`) or MUST surface a `preload_unit_unavailable` warning and continue — a missing preload MUST NOT abort the heartbeat. **Exception: if the unavailable unit also has `guarantee_load: true` in the manifest, the runtime MUST treat unavailability as fatal and MUST abort the heartbeat with a `preload_unit_unavailable` error.** Non-fatal fallback applies only to units with `guarantee_load: false`. In all cases the warning or error MUST be written to the `instruction_audit` table (not only local log) to support replay-based audit (§21.5.3). (S2)
5. Token budget: the combined token cost of boot stub + task-type preloads SHOULD remain under 2000 tokens. Implementations SHOULD emit a `preload_budget_warning` event when this threshold is exceeded but MUST NOT silently drop preloaded units.

Governance:

- Any manifest entry declaring more than **2** `required_by_task_types` values MUST require explicit administrator approval before the manifest can be published (enforced at §21.8.3 as `task_types_approval_required`).
- Build pipelines MUST validate all strings in `required_by_task_types` against the deployment's registered wake-reason enum. Unknown values MUST cause a `task_type_unknown` error at manifest publish time (§21.9).
- The intent of task-type preloads is for structurally-predictable critical units. Authors MUST NOT use `required_by_task_types` as a shortcut to load content that should be retrieved semantically; excessive preload declarations rot into a distributed boot stub.
- **Blast-radius note:** Units declared in `required_by_task_types` are exposed unconditionally to all subsequent task context, including adversarial prompt injections that arrive later in the same heartbeat. Authors SHOULD NOT declare units containing content that must remain confidential from adversarial task payloads. (S3)

---

### §21.2 Instruction Manifest {#section-21-2}

The instruction manifest is a compact, always-loaded index of every instruction unit available to an agent. It fits in the agent's context without incurring meaningful token cost.

#### §21.2.1 Token Budget {#section-21-2-1}

The instruction manifest MUST fit within **1000 tokens** (cl100k). Implementations MUST enforce this at write time and MUST reject a manifest update that would exceed it with error `manifest_too_large` (§21.9). Instruction units SHOULD be described at granular enough detail that `recall_instruction` can select them precisely but coarse enough to stay within budget.

#### §21.2.2 Manifest Entry Shape {#section-21-2-2}

Each instruction unit in the manifest MUST be described by the following fields:

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

| Field | Required | Description |
|---|---|---|
| `name` | MUST | Stable identifier for this instruction unit; MUST be unique within the manifest |
| `description` | MUST | One-line (≤ 120 characters) description of what this unit covers |
| `required_by_task_types` | SHOULD for critical units | Wake-reason strings that cause this unit to be deterministically preloaded at heartbeat start (§21.1.5); entries MUST be registered wake-reason enum values |
| `guarantee_load` | MAY | If `true`, unit is always appended to `recall_instruction` responses regardless of relevance score (§21.3.3); max 5 per agent; requires explicit admin approval; content MUST be safe for any authorised recall caller to observe |
| `load_triggers.intents` | SHOULD | Natural-language intent phrases that SHOULD cause this unit to be loaded |
| `load_triggers.keywords` | SHOULD | Exact or prefix-match keywords; implementations MAY use BM25 matching |
| `load_triggers.task_types` | MAY | Event type strings (e.g. `issue_assigned`) that SHOULD trigger a `recall_instruction` call; distinct from `required_by_task_types` (semantic hint, not deterministic preload) |
| `fact_uri` | MUST if `path` absent | `instruction:`-scope stigmem fact URI for this unit (§21.4) |
| `path` | MUST if `fact_uri` absent | File path relative to the agent's instructions root |
| `token_estimate` | SHOULD | Estimated token count of the full unit content; used for budget planning |

Exactly one of `fact_uri` or `path` MUST be present per entry; an entry with neither or both MUST be rejected with `manifest_entry_invalid`.

> **`required_by_task_types` vs `load_triggers.task_types`:** These are complementary. `required_by_task_types` is a deterministic preload commitment — the runtime unconditionally injects this unit at heartbeat start for the named wake reasons. `load_triggers.task_types` is a semantic hint — it tells the manifest how to describe when a `recall_instruction` call should include this unit, but does not guarantee loading.

#### §21.2.3 Manifest Wire Contract {#section-21-2-3}

The manifest is stored as a stigmem fact under the `instruction:` scope (§21.4) and is also surfaced as a structured API resource. See §21.8.2 and §21.8.3.

---

### §21.3 `recall_instruction` Tool Contract {#section-21-3}

`recall_instruction` is the agent-facing callable that retrieves instruction content on demand. It MUST be available to the agent as a declared tool in all compliant runtimes.

#### §21.3.1 Request Shape {#section-21-3-1}

The request shape is intentionally minimal: the `intent` field is the only
required parameter. `max_chunks` and `token_budget` let the caller balance
context-window cost against coverage. `manifest_hint` provides an escape hatch
for cases where the agent already knows which units it needs, bypassing ranked
retrieval for those specific units.

```json
{
  "intent":        "I need to check out an issue and start work",
  "max_chunks":    3,
  "token_budget":  1200,
  "manifest_hint": ["heartbeat-procedure", "checkout-procedure"]
}
```

| Field | Required | Description |
|---|---|---|
| `intent` | MUST | Free-text description of what the agent is about to do or needs help with |
| `max_chunks` | SHOULD | Maximum number of instruction units to return; MUST default to `3` if absent |
| `token_budget` | SHOULD | Soft token budget for the combined response content; MUST default to `2000` if absent |
| `manifest_hint` | MAY | Explicit unit names from the manifest; these are loaded first before ranked retrieval |

#### §21.3.2 Response Shape {#section-21-3-2}

The response carries the retrieved instruction chunks ranked by relevance,
along with metadata that the agent and runtime need for budget management and
audit. The `audit_token` is a first-class field rather than a header because
the agent must pass it back when submitting usage feedback (§21.5.2) — embedding
it in the body ensures it cannot be silently dropped by middleware.

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

| Field | Description |
|---|---|
| `chunks` | Ordered list of instruction units; most relevant first |
| `chunks[].name` | Unit name from the manifest |
| `chunks[].fact_uri` | Stigmem `instruction:` fact URI |
| `chunks[].content` | Full rendered markdown content of the instruction unit |
| `chunks[].tokens` | Actual token count of `.content` |
| `chunks[].valid_until` | Expiry from the backing stigmem fact; agent SHOULD re-call before expiry if session is long |
| `chunks[].version` | Version string of the instruction unit; used in audit logs |
| `chunks[].score` | Relevance score in [0.0, 1.0] used for ordering |
| `chunks[].source` | Either `"stigmem"` or `"fallback_path"` (§21.6.1 co-existence fallback) |
| `total_tokens` | Sum of tokens across all returned chunks |
| `truncated` | `true` if one or more units were dropped to stay within `token_budget` |
| `missed_hints` | Unit names from `manifest_hint` that were not found or not accessible |
| `audit_token` | Opaque token for the discovery audit; MUST be passed to the audit submission endpoint (§21.5.2) |

#### §21.3.3 Backing Implementation {#section-21-3-3}

`recall_instruction` MUST be implemented as a stigmem `recall` call (§20.3) restricted to the `instruction:` scope (§21.4.1):

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

The `require_garden_ids` constraint MUST be applied so that `recall_instruction` cannot return facts from gardens the agent is not authorized to read (§17, §19.3). Implementations MUST apply the garden ACL check at recall time using the caller's capability token.

If `manifest_hint` is provided, the named units MUST be included in the result (subject to `token_budget`) before the ranked retrieval results. If a hinted unit does not exist or is not accessible, it MUST be silently omitted (not an error) and its name MUST appear in `missed_hints`.

**Guaranteed units (`guarantee_load: true`):** After ranked and hinted results are assembled, the implementation MUST append all manifest units with `guarantee_load: true` that were not already included. The following rules govern their inclusion:

1. **Position:** guaranteed units MUST be appended after ranked results by default, so that ranked results (higher expected relevance) receive attention primacy. A unit with `force_position: "prepend"` in its manifest entry MUST be prepended instead. **A unit with `force_position: "prepend"` MUST undergo explicit content review at manifest publish time, recorded in provenance metadata, and MUST require a distinct admin approval record separate from the general `guarantee_load` approval.** The `force_position: "prepend"` override SHOULD be reserved for universal policy units where omission risk outweighs priming risk. (S6)
2. **Budget precedence:** guaranteed units MUST NOT be silently dropped by `token_budget` exhaustion. If budget is exhausted after ranked results, the implementation MUST still append guaranteed units and MUST set `truncated: true`. Ranked results are truncated first to make room; guaranteed units are truncated last but never to zero.
3. **Agent cap:** at most **5** manifest units **per agent** may have `guarantee_load: true`. Manifest publish MUST be rejected with `guarantee_cap_exceeded` if this per-agent limit would be exceeded (§21.9). A deployment-wide soft cap MAY be configured; exceeding it SHOULD emit a warning event but MUST NOT block individual agent manifest publishes. (S4)
4. **Relevance threshold:** implementations SHOULD warn (non-fatal) if a guaranteed unit has an empirical `P(relevant | recall_invoked) < 0.6` based on the discovery audit; this is a signal to remove the `guarantee_load` flag from that unit.
5. **Governance:** setting `guarantee_load: true` on any manifest entry requires explicit administrator approval. The approval MUST be recorded in the manifest's provenance metadata.
6. **Confidentiality note:** guaranteed units are appended to every `recall_instruction` response and are therefore accessible to any principal authorised to invoke `recall_instruction` for this agent, including via prompt injection. Content in guaranteed units MUST NOT rely on retrieval difficulty for confidentiality. Guaranteed units MUST only contain content that is acceptable for any authorised recall caller to observe. (S5)

#### §21.3.4 Determinism and Auditability {#section-21-3-4}

The same `(intent, manifest_hint, max_chunks, token_budget)` tuple MUST produce the same ordered result given the same set of instruction facts at the same `valid_until` boundaries. This determinism property enables replay-based audit (§21.5.3).

Implementations MUST record every `recall_instruction` invocation in the discovery audit table (§21.5.1) before returning the response. If audit write fails, the response MUST still be returned (audit is best-effort); the failure MUST be logged as `audit_write_failed`.

---

### §21.4 `instruction:` Scope Semantics {#section-21-4}

The `instruction:` URI scheme is a reserved stigmem scope for agent instruction artifacts. It extends §17 (Memory Garden) and §19 (Federation Trust) with instruction-specific semantics.

#### §21.4.1 Scope Namespace {#section-21-4-1}

`instruction:` URIs follow the pattern:

```
instruction:{deployment}/{agent_id}/{unit_name}/{version}
```

Where:
- `{deployment}` is the deployment identifier (e.g. `acme`); MUST match the `entity_uri` root in the org manifest (§19.1).
- `{agent_id}` is the stable agent UUID or a well-known shortname (e.g. `cto`).
- `{unit_name}` is the instruction unit name from the manifest.
- `{version}` is a version string (e.g. `v1`, `v3`); MUST be monotonically incrementing; MUST NOT be a floating alias (e.g. `latest`).

The special URI `instruction:{deployment}/{agent_id}/manifest/{version}` addresses the agent's instruction manifest itself.

#### §21.4.2 Versioning {#section-21-4-2}

Instruction facts are **mutable** in the sense that a new version supersedes the old, but individual versioned facts are **immutable** once written. The following rules apply:

1. A new version MUST be written as a new fact (new `id`, new `version` string) rather than mutating an existing fact.
2. The previous version's `valid_until` MUST be set to the new version's `created_at` within the same transaction, or within a 30-second grace window.
3. `recall_instruction` MUST return only the latest version (highest version string by semantic version ordering, or by `created_at` if versions are non-comparable strings).
4. Agents MAY cache instruction chunks for the duration of a heartbeat/session. Agents MUST NOT cache across heartbeats unless the `valid_until` extends past the next expected heartbeat time.

#### §21.4.3 Provenance {#section-21-4-3}

Every instruction fact MUST carry:

| Field | Requirement |
|---|---|
| `source_trust` | MUST be populated at write time (§19.4); instruction facts authored by verified human administrators SHOULD have `source_trust >= 0.9` |
| `attestation_chain` | MUST include at least one signature from an org manifest key (§19.2); unsigned instruction facts MUST be quarantined (§19.5) |
| `derived_from` | SHOULD reference the instruction unit's prior version hash when updating; `null` is valid for the first version |
| Metadata `authored_by` | MUST be the `entity_uri` of the human or system that created this version |
| Metadata `authored_at` | MUST be an ISO 8601 timestamp |

#### §21.4.4 Garden Membership {#section-21-4-4}

All instruction facts MUST be placed in a dedicated instruction garden, separate from operational fact gardens. The naming convention is:

```
garden_id: "instruction:{deployment}:{agent_id}"
```

Access MUST be restricted to:
- The agent itself: read-only via capability token with verb `read`
- Deployment administrators: read + write via admin API key
- Peer agents: MUST NOT have read access to another agent's instruction garden unless explicitly granted; cross-agent instruction access is a confidentiality boundary (§21.4.5)

#### §21.4.5 Cross-Agent Confidentiality {#section-21-4-5}

An agent's instruction facts MAY contain sensitive operational details including security postures, escalation paths, and negotiation limits. The following rules enforce confidentiality:

1. A capability token granting `read` on `instruction:{deployment}/{agent_A}/*` MUST NOT be derived from a token held by `agent_B` unless `agent_B`'s role is a declared supervisor of `agent_A` in the org manifest.
2. Federation (§19.3) MUST NOT replicate instruction-scope facts to peer nodes unless the receiving node is in the same deployment trust domain.
3. The `recall_instruction` API endpoint MUST validate that the calling agent's token scope matches the instruction garden of the agent whose manifest is being queried; cross-agent recall MUST return `403 instruction_scope_denied`.
4. Audit logs for instruction recall MUST be accessible to administrators but MUST NOT be surfaced to peer agents.

---

### §21.5 Discovery Audit {#section-21-5}

The discovery audit provides a per-heartbeat signal for tuning manifest descriptions and `load_triggers`. It enables evaluation of retrieval quality by comparing what was loaded against what was actually used.

#### §21.5.1 Audit Record Shape {#section-21-5-1}

Each `recall_instruction` invocation produces an audit record that captures
what the agent asked for (`intent`), what was returned (`loaded_chunks`), and —
once the heartbeat completes — what the agent actually used (`used_chunks`) and
what it needed but did not receive (`missed_chunks`). This four-way comparison
is the raw input for the evaluation metrics defined in §21.5.3.

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

| Field | Description |
|---|---|
| `id` | Globally unique audit event ID with `audevent_` prefix |
| `agent_id` | Agent that performed the recall |
| `heartbeat_id` | Run/heartbeat ID in which the recall occurred |
| `session_start` | ISO 8601 timestamp of the heartbeat start |
| `intent` | The `intent` string passed to `recall_instruction` |
| `loaded_chunks` | Unit names returned by `recall_instruction` in this invocation |
| `used_chunks` | Unit names the agent demonstrably applied (runtime-tracked or self-reported) |
| `missed_chunks` | Unit names the agent referenced but that were not in `loaded_chunks` (self-reported or post-hoc replay) |
| `audit_token` | Must match the `audit_token` returned in the `recall_instruction` response |
| `audit_closed` | Timestamp when the audit submission was received; `null` until POST /audit |
| `created_at` | Write timestamp of the initial record |

`used_chunks` and `missed_chunks` MAY be populated by the runtime (if it tracks tool-call traces) or by the agent via self-report at heartbeat end. Agents SHOULD self-report usage when runtime tracking is unavailable.

#### §21.5.2 Audit Submission API {#section-21-5-2}

At the end of a heartbeat, the agent (or runtime) submits usage feedback by
reporting which chunks were actually applied and which were needed but missing.
The `audit_token` from the original `recall_instruction` response ties the
submission to the correct record. This endpoint is idempotent — a duplicate
submission with the same token is a silent success.

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

The audit endpoint MUST be idempotent: a second submission with the same `audit_token` MUST return `204` without modifying the record.

#### §21.5.3 Replay-Based Evaluation {#section-21-5-3}

The audit table is append-only and replay-able. The evaluation metrics are:

**Recall@k**: fraction of `used_chunks` that appear in `loaded_chunks` within rank k.  
**Hit@k**: fraction of heartbeats where at least one `used_chunk` was in `loaded_chunks`.  
**Miss rate**: `|missed_chunks| / (|used_chunks| + |missed_chunks|)`.

These metrics SHOULD be computed over a rolling 7-day window. Deployments SHOULD alert when `miss_rate > 0.15` over 100+ events, as this indicates manifest descriptions or triggers need improvement.

Replay procedure: given an audit record with `intent` and the stigmem state at `session_start`, re-execute `recall_instruction(intent)` and compare results to `loaded_chunks`. Determinism (§21.3.4) guarantees the replay is reproducible.

The `recall@k` and `hit@k` metrics SHOULD be computed against the post-hoc replay set (ground truth: all instruction units the agent actually needed, reconstructed from the full heartbeat trace) to measure manifest coverage independently of what the agent happened to load.

> **Known limitation — endogeneity of `used_chunks` (non-normative):** Recall@k, Hit@k, and miss rate are all computed relative to `used_chunks`, which is itself derived from agent behavior during the heartbeat being measured. An agent that chronically fails to load a required instruction unit will never reference it, so the unit will never appear in `used_chunks`. The chronic miss is therefore invisible to all three live-audit metrics. This is an accepted limitation for the design: the live audit is a useful signal for units the agent *does* interact with, but it cannot independently surface units the agent has never successfully retrieved.
>
> #### 21.5.4 Probe-Set Eval (follow-on, non-normative)
>
> To complement the endogenous live-audit metrics with an exogenous coverage signal, implementations SHOULD maintain a **probe set**: a curated list of `(intent, required_units)` pairs administered independently of the live agent. After every manifest update and on a periodic schedule (e.g. daily), run `recall_instruction(intent)` against each probe and compute:
>
> **Probe-coverage@k**: fraction of `required_units` in each probe that appear in the top-k recall result.  
> **Probe-hit@k**: fraction of probes where ≥ 1 `required_unit` appears in the top-k result.
>
> Unlike live-audit Recall@k, these metrics are independent of agent behavior — a chronically un-loaded unit will fail the probe that covers it even if no live heartbeat ever referenced it.
>
> The probe set SHOULD be curated by deployment administrators. Each probe entry MUST specify:
>
> ```json
> {
>   "probe_id":       "probe_heartbeat_start",
>   "intent":         "I am starting a new heartbeat and need to know what to do",
>   "required_units": ["heartbeat-procedure", "checkout-procedure"],
>   "k":              3
> }
> ```
>
> A follow-on spec revision (the pre-reset multi-backend work) will formalize the probe-set storage format, the evaluation runner contract, alert thresholds, and the soft-lift mechanism described below.
>
> #### 21.5.5 Probe-Set Coverage Sampling with Soft Score Lift (the pre-reset multi-backend work roadmap, non-normative)
>
> Approaches B and augmented A (§21.1.5, §21.8.3) address structurally-predictable and trigger-quality misses at authoring time. The residual problem — semantic-drift misses and embedding-model staleness causing gradual coverage degradation without any live-audit signal — requires an exogenous coverage signal independent of both the retrieval path and agent behavior.
>
> **Architecture (non-normative):**
>
> 1. **Probe-set construction:** At manifest publish time, generate M=15–20 synthetic queries per unit by combining the unit's `description` with each `load_triggers.intents` string, paraphrased via a diverse augmentation pass (lexical + syntactic variation, not just dense neighbours). Store per unit as `{unit_id → [q_1 … q_M]}` in the manifest DB. Re-generated on unit update.
>
> 2. **Background coverage audit:** A scheduled job (runs daily and on every embedding-model version bump) runs all probes through the live retrieval index. Computes per-unit `hit@10` across the M probes. Units with `hit@10 < 0.4` are flagged as *coverage-critical*.
>
> 3. **Soft score lift for coverage-critical units:** Flagged units receive a log-additive ranking boost applied within the recall engine: `score += log(1 + λ)` where λ ≈ 0.15. This lifts chronically under-retrieved units without forcing them into context unconditionally — they only appear if they are in the semantic neighbourhood of the actual query. No irrelevant units are injected; the noise properties of Approach C are avoided entirely.
>
> 4. **Coverage endpoint:** `GET /v1/agents/{agent_id}/instruction-manifest/coverage` (§21.8.6) returns per-unit `hit@10` and `coverage_status` so authors can diagnose units before production misses occur.
>
> 5. **Probe-set calibration:** The probe set SHOULD be seeded with real heartbeat intent strings (10% sample, PII-stripped) on a weekly cadence to keep the distribution calibrated to actual agent query patterns.
>
> This approach addresses the root cause of endogeneity by making the miss-rate signal exogenous, and makes embedding-model drift visible as a measurable per-unit delta across versions.

---

### §21.6 Migration Semantics {#section-21-6}

This section defines the co-existence and deprecation path for agents transitioning from file-based instructions to `instruction:`-scope stigmem facts.

#### §21.6.1 Co-existence Period {#section-21-6-1}

During migration, an agent MAY have both:
- A static markdown instruction file (e.g. `AGENTS.md`) at a file path, and
- A manifest with `fact_uri` entries pointing at stigmem.

The following resolution rules apply:

1. If a manifest entry has both `fact_uri` and `path`, `fact_uri` MUST take precedence.
2. If `fact_uri` lookup fails (fact not found or scope unreachable), the runtime MUST fall back to `path` if present and MUST append `"source": "fallback_path"` to the returned chunk.
3. File-path entries are read-only; they MUST NOT be written via `recall_instruction` or the instruction API.
4. The boot stub MUST indicate migration state via the `migration_mode` frontmatter field:
   - `"file"` — no manifest; static file only
   - `"coexistence"` — both static file and manifest entries present
   - `"stigmem"` — manifest only; no file fallback

#### §21.6.2 Deprecation Path {#section-21-6-2}

The deprecation sequence for an instruction unit is:

| Stage | Action |
|---|---|
| 1. Seed | Write instruction content to stigmem as `instruction:` facts; verify recall quality over ≥ 5 heartbeats |
| 2. Coexist | Add `fact_uri` to the manifest entry alongside existing `path`; set `migration_mode: "coexistence"` |
| 3. Verify | Monitor audit metrics (§21.5.3) for 7 days; confirm `miss_rate < 0.10` |
| 4. Promote | Remove `path` from the manifest entry; set `migration_mode: "stigmem"` |
| 5. Archive | Move the source markdown file to `docs/legacy-instructions/` with a redirect comment pointing to the `fact_uri` |

Deployments MUST NOT skip Stage 3 (Verify) for agents that handle sensitive operational decisions. The risk of an undetected miss in a security-relevant instruction unit is higher than the cost of a 7-day observation window.

#### §21.6.3 Bulk Migration Tooling {#section-21-6-3}

Implementations SHOULD provide a `stigmem migrate-instructions` CLI command that:

1. Reads all entries from an existing markdown instruction file.
2. Splits at H2/H3 section boundaries (or at a configurable split regex).
3. Writes each section as an `instruction:` fact with attestation from the local admin key.
4. Emits a manifest `entries` array for copy-paste into the manifest file.
5. Does NOT automatically update the manifest or boot stub; the operator MUST review and commit the change manually.

This is a SHOULD (not MUST) because manual migration is always acceptable.

---

### §21.7 Schema Migrations {#section-21-7}

The following DDL MUST be applied when upgrading to pre-reset instruction-discovery design (§21 compliance).
Three tables support the lazy instruction layer:

**`instruction_manifests`** stores versioned snapshots of each agent's
instruction manifest. Previous versions are retained (with a `superseded_at`
timestamp) so that the audit system can replay recalls against the manifest
that was active at the time.

**`instruction_audit`** is the append-only log backing the discovery audit
(§21.5). Each row captures one `recall_instruction` invocation and its
usage-feedback follow-up.

**`boot_stubs`** caches the rendered boot stub for each `(agent_id,
adapter_profile)` pair. The cache is invalidated whenever the agent's manifest
version changes or the stub schema version increments.

```sql
-- Instruction manifest registry
CREATE TABLE IF NOT EXISTS instruction_manifests (
    id               TEXT PRIMARY KEY,           -- UUID
    agent_id         TEXT NOT NULL,
    version          TEXT NOT NULL,
    fact_uri         TEXT NOT NULL,              -- instruction: scope URI
    token_count      INTEGER NOT NULL,
    body             TEXT NOT NULL,              -- JSON: array of manifest entries
    created_at       INTEGER NOT NULL,           -- Unix ms
    superseded_at    INTEGER,                    -- NULL if current version
    UNIQUE(agent_id, version)
);
CREATE INDEX IF NOT EXISTS idx_manifests_agent ON instruction_manifests (agent_id, superseded_at NULLS FIRST);

-- Discovery audit log (append-only)
CREATE TABLE IF NOT EXISTS instruction_audit (
    id               TEXT PRIMARY KEY,           -- audevent_ prefixed UUID
    agent_id         TEXT NOT NULL,
    heartbeat_id     TEXT NOT NULL,
    session_start    INTEGER NOT NULL,           -- Unix ms
    intent           TEXT NOT NULL,
    loaded_chunks    TEXT NOT NULL,              -- JSON array of unit names
    used_chunks      TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    missed_chunks    TEXT NOT NULL DEFAULT '[]', -- JSON array; updated on POST /audit
    audit_token      TEXT NOT NULL UNIQUE,
    audit_closed     INTEGER,                    -- Unix ms; NULL until POST /audit received
    created_at       INTEGER NOT NULL            -- Unix ms
);
CREATE INDEX IF NOT EXISTS idx_audit_agent_session ON instruction_audit (agent_id, session_start DESC);
CREATE INDEX IF NOT EXISTS idx_audit_token         ON instruction_audit (audit_token);

-- Boot stub cache (invalidated on manifest update)
CREATE TABLE IF NOT EXISTS boot_stubs (
    agent_id          TEXT NOT NULL,
    adapter_profile   TEXT NOT NULL DEFAULT 'generic',
    stub_version      INTEGER NOT NULL DEFAULT 1,
    body              TEXT NOT NULL,              -- full markdown stub
    token_count       INTEGER NOT NULL,
    generated_at      INTEGER NOT NULL,           -- Unix ms
    manifest_version  TEXT NOT NULL,              -- version string of backing manifest
    PRIMARY KEY (agent_id, adapter_profile)
);
```

---

### §21.8 Wire Format Additions {#section-21-8}

The following routes supplement §5. Implementations MUST provide all MUST-labelled routes to claim §21 compliance.

#### §21.8.1 Get Boot Stub (MUST) {#section-21-8-1}

Returns the agent's rendered boot stub as a markdown document. The response
includes headers that let the runtime verify freshness: `X-Stub-Version` is
the stub schema version, `X-Manifest-Version` is the backing manifest version,
and `X-Token-Count` is the stub's token cost. Only the agent itself or an admin
may call this endpoint — a peer agent requesting another agent's stub is
rejected with 403 to enforce instruction confidentiality (§21.4.5).

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

If `profile` is absent, MUST default to `generic`. Unknown profiles MUST be treated as `generic` (no error).

#### §21.8.2 Get Instruction Manifest (MUST) {#section-21-8-2}

Retrieves the current (non-superseded) instruction manifest for an agent. The
response is a structured JSON object containing the manifest version, backing
stigmem fact URI, token count, and the full array of manifest entries (§21.2.2).
This is the endpoint the boot stub references at `manifest_uri` — but it is
also useful for operators inspecting an agent's configuration.

```
GET /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <agent api-key or admin api-key>

→ 200 {
    "manifest_version": "v3",
    "fact_uri": "instruction:acme/agent/cto/manifest/v3",
    "token_count": 840,
    "entries": [ ...entry objects per §21.2.2... ],
    "last_updated_at": "2026-05-04T00:00:00Z"
  }
→ 403 if caller is not the agent itself or an admin
→ 404 if no manifest configured for agent
```

#### §21.8.3 Publish / Replace Instruction Manifest (MUST) {#section-21-8-3}

Publishes a new version of the agent's instruction manifest, replacing the
current version. This endpoint is the gate through which all manifest changes
must pass — it enforces the token budget (1000 tokens), validates entry
structure, runs the paraphrase coverage gate (Approach A), and atomically
updates the backing stigmem fact, the `instruction_manifests` table, and the
boot stub cache. Manifest versions are immutable: once a version string is
published, it cannot be overwritten (409 on collision).

```
PUT /v1/agents/{agent_id}/instruction-manifest
Authorization: Bearer <admin api-key>
Content-Type: application/json

{
  "version": "v4",
  "entries": [ ...entry objects per §21.2.2... ],
  "skip_coverage_gate": false
}

→ 200 {
    "fact_uri":       "instruction:acme/agent/cto/manifest/v4",
    "token_count":    910,
    "coverage_report": [
      { "unit": "security-posture", "coverage_pct": 0.95, "passed": true },
      { "unit": "escalation-path",  "coverage_pct": 0.60, "passed": false }
    ]
  }
→ 400 manifest_too_large              if token_count > 1000
→ 400 manifest_entry_invalid          if any entry has neither or both of fact_uri/path
→ 400 manifest_coverage_failure       if any unit fails the paraphrase coverage gate (see below)
→ 400 task_type_unknown               if any required_by_task_types value is not a registered wake-reason string
→ 400 guarantee_cap_exceeded          if more than 5 entries have guarantee_load: true
→ 400 task_types_approval_required    if any entry declares > 2 required_by_task_types values without recorded admin approval
→ 409 manifest_version_conflict       if version already exists (versions are immutable)
```

**Augmented manifest coverage gate (Approach A):** This route MUST run a paraphrase-expansion coverage check before accepting a manifest. For each unit in the incoming manifest:

1. For every string in `load_triggers.intents`, generate N=5 paraphrases using lexically and syntactically diverse augmentation (MUST NOT use the retrieval encoder's own nearest-neighbour space as the sole paraphrase source).
2. Run `recall_instruction(paraphrase)` for each generated paraphrase and check whether this unit appears in the top-k results (default k=3).
3. Compute `coverage_pct = (paraphrases where unit in top-k) / (total paraphrases)`.
4. If `coverage_pct < 0.80` for any unit, the entire publish MUST be rejected with `manifest_coverage_failure`, identifying the failing unit(s).

`skip_coverage_gate: true` MAY be used by administrators to bypass the coverage check (e.g. for bootstrap or emergency update); the bypass MUST be recorded in the manifest's provenance metadata and MUST emit an audit event that includes the names and `coverage_pct` values of all units that would have failed the gate. **When `skip_coverage_gate: true` is used on a manifest containing any `guarantee_load: true` entry, the bypass provenance record MUST include co-signatures from at least two distinct administrators (two distinct `authored_by` entity URIs). Single-admin bypass is permitted only for manifests with no `guarantee_load: true` entries.** (S7) Implementations SHOULD automatically schedule re-certification within 7 days when `skip_coverage_gate: true` is used. (S10)

**Paraphrase generator data boundary:** Paraphrase generation input MUST be limited to `load_triggers.intents` strings only. Instruction fact content (the body of instruction units) MUST NOT be sent to any external paraphrase generation service. If an external service is used for paraphrase generation, it MUST be listed in the deployment's trust manifest (§19.1) and covered by an appropriate data processing agreement. Implementations SHOULD prefer local, deterministic paraphrase methods for deployments handling confidential instruction content. (S8)

**Re-certification requirement:** When the deployment's embedding model version changes, all existing manifests MUST be re-certified through this gate before the new model version is activated for production recall. Implementations MUST expose the current embedding model version in the `GET /v1/agents/{agent_id}/instruction-manifest` response.

This route MUST atomically: (1) run coverage gate, (2) write the manifest fact to stigmem under `instruction:` scope, (3) update `instruction_manifests` table, (4) invalidate the boot stub cache for this agent.

#### §21.8.4 Recall Instructions (MUST) {#section-21-8-4}

This is the HTTP route that backs the `recall_instruction` tool contract
(§21.3). The agent's runtime calls this endpoint on behalf of the agent when
it invokes the tool. Scope validation ensures that an agent can only recall
its own instructions — cross-agent recall is rejected with 403
`instruction_scope_denied`.

```
POST /v1/agents/{agent_id}/recall-instruction
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "intent":        "I need to check out an issue and start work",
  "max_chunks":    3,
  "token_budget":  1200,
  "manifest_hint": ["heartbeat-procedure"]
}

→ 200 { ...response shape per §21.3.2... }
→ 400 intent_required          if intent is absent or empty
→ 403 instruction_scope_denied if agent token scope does not match agent_id
→ 404 if agent not found
→ 503 recall_backend_unavailable if stigmem recall backend is unreachable (retryable)
```

#### §21.8.5 Submit Discovery Audit (SHOULD) {#section-21-8-5}

The wire-level route for the audit submission described in §21.5.2. This is a
SHOULD (not MUST) because the audit is best-effort — an agent that cannot
submit usage feedback does not break the instruction system, it only degrades
evaluation quality. The request body and semantics are identical to §21.5.2.

```
POST /v1/instruction/audit
Authorization: Bearer <agent api-key>
Content-Type: application/json

{
  "audit_token":   "audi_01J...",
  "used_chunks":   ["heartbeat-procedure"],
  "missed_chunks": []
}

→ 204 on success (idempotent)
→ 400 audit_token_invalid  if token not recognized or already fully closed
→ 400 audit_token_expired  if token is older than 24 hours
```

#### §21.8.6 Get Manifest Coverage Report (SHOULD) {#section-21-8-6}

Returns per-unit retrieval quality metrics for the agent's current manifest.
This is the primary operator tool for diagnosing instruction units that may be
under-retrieved before they produce production misses. Agent-key callers
receive only raw numeric metrics; admin-key callers also receive the
`coverage_status` categorical label to limit the retrieval-quality oracle
surface for non-admin callers (§22 S11).

```
GET /v1/agents/{agent_id}/instruction-manifest/coverage
Authorization: Bearer <agent api-key or admin api-key>

Agent-key response:
→ 200 {
    "manifest_version": "v4",
    "embedding_model_version": "nomic-embed-text-v1.5",
    "evaluated_at": "2026-05-04T06:00:00Z",
    "units": [
      {
        "name":             "security-posture",
        "coverage_pct":     0.95,
        "hit_at_10":        0.92,
        "probe_count":      20,
        "last_evaluated_at": "2026-05-04T06:00:00Z"
      }
    ]
  }

Admin-key response: same as above, plus "coverage_status" field per unit.

→ 403 instruction_scope_denied  if agent API key's scope does not match {agent_id}
→ 403 if peer agent's API key is used to query another agent's coverage
→ 404 if no manifest or no coverage report generated yet
```

**Scope validation (S9):** The `agent_id` path parameter MUST be validated against the caller's API key scope. An agent API key MUST only grant access to the coverage report for the agent whose scope matches the token. A peer agent's API key querying a different agent's coverage report MUST return `403 instruction_scope_denied`. Only an admin API key may access any agent's coverage report.

**Categorical label restriction (S11):** The `coverage_status` categorical label (`"ok"`, `"coverage_critical"`, `"not_evaluated"`) SHOULD be returned only in admin-key responses. Agent-key responses SHOULD return only raw `coverage_pct` and `hit_at_10` values, omitting the categorical label. This limits the retrieval-quality oracle surface for non-admin callers.

`coverage_status` values (admin-only): `"ok"` (hit@10 ≥ 0.4), `"coverage_critical"` (hit@10 < 0.4, soft-lift eligible in the pre-reset multi-backend work), `"not_evaluated"` (probe run not yet completed). This endpoint is the primary operator signal for diagnosing instruction units before they produce production misses.

---

### §21.9 Error Reference {#section-21-9}

| HTTP | Error code | Condition |
|---|---|---|
| 400 | `intent_required` | `intent` field absent or empty in `recall_instruction` request |
| 400 | `manifest_too_large` | Manifest exceeds 1000-token budget |
| 400 | `manifest_entry_invalid` | Entry has neither `fact_uri` nor `path`, or has both |
| 400 | `manifest_coverage_failure` | One or more units failed the paraphrase coverage gate at publish time (§21.8.3); response body identifies failing units and their `coverage_pct` |
| 400 | `task_type_unknown` | A `required_by_task_types` value is not a registered wake-reason string in this deployment |
| 400 | `guarantee_cap_exceeded` | More than 5 manifest entries have `guarantee_load: true`; deployment cap exceeded |
| 400 | `task_types_approval_required` | A manifest entry declares > 2 `required_by_task_types` values and no admin approval is recorded |
| 400 | `audit_token_invalid` | `audit_token` not recognized or already fully closed |
| 400 | `audit_token_expired` | `audit_token` is older than 24 hours |
| 403 | `instruction_scope_denied` | Caller's token scope does not match the requested agent's instruction garden |
| 404 | `manifest_not_found` | No instruction manifest configured for the agent |
| 404 | `boot_stub_not_found` | No boot stub generated for the agent yet |
| 409 | `manifest_version_conflict` | Version string already exists; manifest versions are immutable |
| 503 | `recall_backend_unavailable` | Stigmem recall backend unreachable; retryable |

---

## Subsection anchors {#subsection-anchors}

*Anchors below are provided so docs links to specific subsections always resolve, even when the subsection text lives only in earlier spec drafts.*

### §21.5.4 {#section-21-5-4}
