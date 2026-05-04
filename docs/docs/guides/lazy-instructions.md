---
id: lazy-instructions
title: Lazy Instruction Discovery
sidebar_label: Lazy Instruction Discovery
description: Replace full instruction-file preloads with a boot stub + on-demand recall. Covers boot stub format, manifest schema, chunk authoring, and load-trigger design.
---

# Lazy Instruction Discovery

**Audience:** Agent operators authoring or migrating instruction files for Stigmem-backed agents.  
**Spec reference:** §21 Lazy Instruction Discovery (Phase 10).

---

Without lazy discovery, every conversation start loads the agent's entire instruction set — role spec, heartbeat checklist, tool lists, memory files — whether or not most of it is relevant to the current task. Lazy instruction discovery replaces that preload with two small, stable artifacts:

1. **Boot stub** (~300–500 tokens) — identity, role summary, and a `recall_instruction` tool pointer. Always loaded.
2. **Instruction manifest** (~500–1 500 tokens depending on instruction count) — a compact index of every instruction unit with descriptions and load triggers. Always loaded.

The agent calls `recall_instruction(intent)` at each turn to pull relevant chunks on demand. Only content that scores above the retrieval threshold is loaded into context.

**Measured result:** In two production rollouts, agents reduced per-turn instruction token consumption to **13–50%** of their eager baseline with **100% coverage** of task-critical instruction sections across all representative heartbeats.

---

## Boot stub format

The boot stub is the only file the harness loads at agent startup. It must contain:

| Field | Required | Description |
|-------|----------|-------------|
| `stub_version` | yes | Integer schema version (currently `2`). |
| `migration_mode` | yes | `eager` (for rollback) / `shadow` (dual-load for audit) / `lazy` (production). |
| `agent_id` | yes | Agent UUID — used to scope recall queries. |
| `role` | yes | Role display name used in `recall_instruction` queries. |
| `manifest_path` | yes | Relative or absolute path to `manifest.json`. |
| `max_chunks` | yes | Maximum instruction chunks to load per turn. Start at `4`; tune based on shadow audit. |
| `recall_tool` | yes | Tool name the harness exposes for on-demand recall (default: `recall_instruction`). |
| `identity_summary` | yes | 2–4 sentence role summary. This is the agent's entire identity context at turn start. |
| `heartbeat_contract` | recommended | One-sentence pointer to the heartbeat procedure chunk. Avoids a recall miss on the very first turn. |

### Minimal example

```yaml
# boot_stub.md
---
stub_version: 2
migration_mode: lazy
agent_id: a1b2c3d4-0000-0000-0000-000000000001
role: backend-engineer
manifest_path: ./instructions/manifest.json
max_chunks: 4
recall_tool: recall_instruction
---

You are a backend-engineer agent. Check the manifest and call
`recall_instruction` for task-specific instructions.

heartbeat_contract: "Follow the heartbeat procedure in the
`heartbeat-checklist` chunk before exiting any turn."
```

:::tip Set `max_chunks: 4` by default
Two production rollouts found that `max_chunks: 3` was too tight: the heartbeat-entry chunk, one task-specific chunk, and the exit chunk consumed all three slots, leaving no room for role-specific content. `max_chunks: 4` reliably fit all critical chunks and stayed well within token budgets.
:::

:::info Production reference: CTO agent (small instruction set)
The CTO agent runs `stub_version: 2`, `migration_mode: lazy`, `max_chunks: 4`. Eager baseline: 1,129t (11 chunks). Eval-phase token range: 356–565t (31.5–50.0% of baseline). 11/11 eval heartbeats at 100% critical coverage, 0 regressions. See [Shadow mode audit](#shadow-mode-audit) for the bimodal token profile and keyword lessons from this rollout.
:::

---

## Instruction manifest schema

The manifest is a JSON file (or a Stigmem fact with relation `instruction:manifest`) with this structure:

```json
{
  "manifest_version": "1",
  "agent_id": "a1b2c3d4-0000-0000-0000-000000000001",
  "role": "backend-engineer",
  "total_eager_tokens": 1129,
  "chunks": [
    {
      "name": "work-standards",
      "fact_uri": "instruction:default/agent/a1b2c3d4.../work-standards/v1",
      "description": "Commit message format, code-review standards, done criteria, and bug-fix discipline.",
      "tokens": 162,
      "load_triggers": {
        "keywords": ["commit", "review", "code", "implement", "test", "bug", "fix", "pr", "done"],
        "task_types": ["implementation", "code_review", "bug_fix", "testing"],
        "intent_patterns": ["how do I", "what are the standards", "review checklist"]
      }
    },
    {
      "name": "exit",
      "fact_uri": "instruction:default/agent/a1b2c3d4.../exit/v1",
      "description": "Exit checklist: what to do before ending a turn — post comment, update status.",
      "tokens": 88,
      "load_triggers": {
        "keywords": ["exit", "wrap", "done", "complete", "finish", "final", "closing", "conclude"],
        "task_types": ["any"],
        "intent_patterns": ["before I finish", "end of turn", "post update"]
      }
    }
  ]
}
```

### `load_triggers` fields

| Field | Type | Description |
|-------|------|-------------|
| `keywords` | `string[]` | Token-overlap signals. The recall pipeline treats these as lexical hints. Include natural-language synonyms, not just internal identifiers. |
| `task_types` | `string[]` | Task categories that always need this chunk (`implementation`, `code_review`, `bug_fix`, `any`). |
| `intent_patterns` | `string[]` | Short natural-language phrases the agent or harness might use when querying. |

### `total_eager_tokens`

Record the total token count of all chunks when fully loaded. This becomes the baseline for shadow-audit comparisons.

---

## Chunk authoring: file vs. section

The migration tool splits markdown files on H1/H2/H3 headings by default. Each heading becomes one chunk. Authoring guidance:

| When to keep as one chunk | When to split |
|--------------------------|---------------|
| Content always needed together (e.g., a short procedure with 3 steps) | Content with distinct, independently-useful topics |
| Content under ~400 tokens | Content over ~600 tokens |
| Content with the same recall trigger profile | Content that belongs to different task types |

**Anti-patterns:**
- Putting unrelated content in one heading to save manifest entries. Each recall call loads up to `max_chunks` entries; granularity is free.
- Creating chunks so small (&lt;20 tokens) they add manifest overhead without meaningful content.

---

## Load-trigger design

Load triggers are the single biggest lever on recall coverage. Two production rollouts found the same root cause at their first miss: **trigger keywords were too narrow** — written in internal-doc vocabulary rather than the natural-language intents that trigger recall queries.

### Rule 1 — Include completion synonyms on every exit/wrap-up chunk

Any chunk describing what to do at end-of-turn (post comment, update status, commit changes) must include the full set of completion synonyms:

```json
"keywords": ["exit", "wrap", "done", "complete", "finish", "final", "closing", "conclude", "end"]
```

Without these, the chunk misses recall on every standard-task heartbeat despite being needed on every one.

### Rule 2 — Include task-verb synonyms on work-standards chunks

Any chunk describing how to do a type of work (code review, implementation, debugging) must include all common task verbs for that work type:

```json
"keywords": ["review", "code", "implement", "test", "bug", "fix", "refactor", "pr", "pull request"]
```

In the CTO production rollout (HB3), a `work-standards` chunk with no task-verb triggers scored zero hits on a pure code-review intent and was absent — a regression. Adding `["review", "code", "implement", "test", "bug", "fix"]` resolved it in the next heartbeat and held for all subsequent turns. Work-standards chunks are critical on almost every engineering task; their keywords must cover every entry point verb, not just the verb that describes the chunk's own content.

### Rule 3 — Check for natural-language vs. identifier drift

If a keyword only makes sense to someone who knows the document structure (`HEARTBEAT-9-exit`, `SOUL-philosophy`), add the natural-language equivalents. The recall engine scores semantic similarity — use the words the agent and users actually type.

### Rule 4 — Add `task_types: ["any"]` sparingly

Chunks that are truly needed on every turn (the heartbeat checklist, the exit procedure) can use `"task_types": ["any"]`. Do not overuse this — it defeats the token-budget purpose of lazy loading.

---

## Token budget planning

When sizing `max_chunks`, plan for the worst case: a heartbeat where the agent needs task-entry instructions, task-body instructions, and an exit checklist simultaneously.

| Rule of thumb | Guidance |
|---------------|----------|
| Start with `max_chunks: 4` | Fits task-entry + 2 task-specific + exit reliably |
| Target < 50% of eager baseline at median | Leaves headroom for one unexpected chunk |
| Check p95, not just median | In shadow mode, log per-heartbeat token totals and inspect the 95th percentile |
| Raise `max_chunks` before adding more keywords | If coverage is low, the fix is usually more slots, not more keywords |

### Calibrating for small instruction sets

For agents with fewer than ~1 500 total eager tokens, the 25% ceiling from the standard eval criterion is often too tight — recall@4 will naturally land at 40–50% because the chunks themselves are closer to the token-budget ceiling. The right calibration:

- Small sets (< 1 500t): target ≤ 50% of eager baseline.
- Large sets (> 3 000t): target ≤ 25% of eager baseline.

Both targets represent real savings: 50% reduction on a 1 200-token set saves 600 tokens/turn; 87% reduction on a 3 200-token set saves ~2 800 tokens/turn.

---

## Shadow mode audit

Before flipping to lazy mode, run shadow mode for at least 10 representative turns. Shadow mode loads both the full eager set and the lazy-recall set, then records coverage and token delta.

```bash
# Set migration_mode: shadow in boot_stub.md, then observe:
stigmem instruction audit \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --format table

# Sample output:
# Turn  Intent              Lazy tokens  % baseline  Coverage  Regressions
# 1     setup/migration     310t         27.5%       100%      0
# 2     task-execution      525t         46.5%       100%      0
# 3     code-review         565t         50.0%       100%      0
# …
```

**Pass criteria before flipping:**

| Criterion | Recommended target |
|-----------|-------------------|
| Coverage | ≥ 95% across all audit turns |
| Token budget | < 25% of eager for large sets; < 50% for small sets |
| Regressions | 0 |

When coverage dips below 95%, inspect the missed chunk and add keywords. See [Tutorial: Authoring Lazy-Discovery Instructions](/docs/tutorials/authoring-lazy-discovery-instructions) for a worked example with before/after measurements.

### Production rollout summary

Two production agents have completed the shadow audit and flipped to lazy mode:

| Agent | Eager baseline | Eval token range | % baseline | Eval HBs | Coverage | Regressions |
|---|---|---|---|---|---|---|
| CEO (large set) | 3,190t | 415t stable | 13.0% | 11/11 | 100% | 0 |
| CTO (small set ≤ 1,500t) | 1,129t | 356–565t bimodal | 31.5–50.0% | 11/11 | 100% | 0 |

**CTO bimodal profile.** The CTO agent's token load splits into two stable bands by intent class:

- **457t (40.5%)** — bug-fix, CI/CD, refactor, security: `work-standards` dominates (3–4 keyword hits), filling the remaining slots with `exit`, `technical-lenses`, `soul`.
- **565t (50.0%)** — architecture, data-model, spec, performance: `what-you-own` and `technical-lenses` both fire on architecture/technical/implementation keywords, pushing to the 50% ceiling while still covering all critical chunks.

The bimodal shape is structural, not a tuning gap. Architecture intents legitimately need two scope chunks; the budget ceiling is by design. If your agent shows a similar bimodal pattern, verify that critical chunks (work-standards, exit) are always present in both bands before accepting it as stable.

---

## Instruction scope confidentiality

**Spec reference:** §21.4 (v1.1-draft rev 6; SE-reviewed rev 10).

Facts stored under the `instruction:` scope are accessible to any caller authorized on the agent — including calls triggered by adversarial prompt injection. **Content MUST NOT rely on retrieval difficulty as a confidentiality control.**

Practical implications:

- **Do not store secrets in instruction facts.** API keys, internal system credentials, and sensitive configuration belong in environment variables or a secrets manager — not in instruction units.
- **`guarantee_load: true` units are always exposed.** A unit marked `guarantee_load: true` is injected into every heartbeat regardless of task intent, making its content visible in every prompt context including those shaped by attacker-controlled input. Reserve `guarantee_load` for non-sensitive policy content (mandatory escalation thresholds, hard prohibitions).
- **`force_position: "prepend"` requires admin approval.** Units set to prepend before the boot stub require a distinct admin approval record (§21.3.3 rule 1). This gate exists because prepended units appear before any trust-filtering logic.
- **All instruction reads are auditable.** Every `recall_instruction` call produces an `audit_token` (§21.5). Operators can audit which instruction units were loaded per heartbeat via `POST /v1/instruction/audit`.

:::warning
Instruction content is not private. An attacker who can influence the agent's prompt context can potentially elicit any instruction unit's content regardless of whether that unit would normally be recalled. Write instruction files assuming their content may be observable.
:::

---

## Discovery audit eval metrics

**Spec reference:** §21.5 (v1.1-draft rev 6; RS-reviewed rev 9).

The shadow audit protocol produces per-heartbeat metrics for evaluating recall quality. Three primary metrics:

| Metric | Definition | Pass threshold |
|--------|-----------|----------------|
| **Recall@k** | Fraction of recalled chunks that were task-critical, across all audit turns | ≥ 0.95 |
| **Hit@k** | Fraction of task-critical chunks present in the top-k recall results for a given turn | ≥ 0.95 per turn |
| **Miss rate** | Fraction of turns where at least one task-critical chunk was absent from the recall set | ≤ 0.05 |

These are computed by the `stigmem instruction audit` command. The audit compares recalled chunks against the set of chunks that *would have been loaded* under eager mode (the ground truth), not against an agent-reported usage log.

:::info Endogeneity caveat (§21.5.3)
Live-audit metrics derived from `used_chunks` (what the agent actually called) have an endogeneity limitation: **chronic misses are invisible**. If a chunk is never recalled because its triggers are too narrow, the agent never reports needing it, so the miss never surfaces in Recall@k or Hit@k. The replay-based eval (shadow mode with eager ground truth) is the authoritative measure. See §21.5.4 for the probe-set complement: curated `(intent, required_units, k)` probes that test chunk coverage independently of agent behavior.
:::

### Probe-set evaluation (§21.5.4, non-normative)

For operators who want to go beyond shadow mode, the spec defines a non-normative probe-set approach:

1. Curate a set of `(intent, required_units, k)` probes — representative task intents paired with the chunks that MUST be recalled for that intent.
2. Run each probe through `recall_instruction` and measure **Probe-coverage@k** (fraction of required units in top-k) and **Probe-hit@k** (binary: all required units present at k?).
3. Probe-set metrics are independent of agent behavior, making them immune to the endogeneity limitation above.

This is the recommended pre-production gate for agents with large instruction sets (> 20 chunks) before flipping to `migration_mode: lazy`.

---

## Related

- [Instruction Migration guide](/docs/guides/instruction-migration) — `stigmem instruction migrate` CLI reference
- [Recall guide](/docs/guides/recall) — the underlying recall pipeline (§20.3)
- [Tutorial: Authoring Lazy-Discovery Instructions](/docs/tutorials/authoring-lazy-discovery-instructions) — end-to-end walkthrough with real coverage and token numbers
