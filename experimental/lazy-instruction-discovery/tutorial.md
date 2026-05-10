---
title: "Tutorial: Authoring Lazy-Discovery Instructions"
sidebar_label: Authoring Lazy-Discovery Instructions
description: A concrete walkthrough — migrate an instruction set to lazy discovery, tune manifest triggers, run a shadow audit, and flip. Includes real coverage and token numbers from two production rollouts.
audience: Integrator
---

# Tutorial: Authoring Lazy-Discovery Instructions

**Audience:** Agent operators migrating an existing instruction set to lazy discovery.  
**Spec references:** §21 Lazy Instruction Discovery, §20.3 Recall API.  
**Time:** ~45 minutes, plus the time for a 10–14 turn shadow audit.

---

## What you will achieve

Two production agents — a project-manager agent and a backend-engineer agent — were migrated to lazy discovery during the pre-reset instruction-discovery design. The results:

| Agent type | Eager tokens/turn | Lazy tokens/turn | % of baseline | Coverage |
|------------|-------------------|-----------------|---------------|----------|
| Project-manager (large instruction set, 23 chunks) | ~3,190t | 415t | **13%** | 100% |
| Backend-engineer (compact instruction set, 11 chunks) | 1,129t | 356–565t | **31–50%** | 100% |

Both reached 100% task-critical instruction coverage with zero regressions across 11 consecutive representative turns. The project-manager agent hit all pass criteria — ≥ 95% coverage, < 25% token budget — starting at turn 4.

This tutorial follows the same steps those rollouts used.

---

## Prerequisites

- A running Stigmem node (`stigmem start`, default `http://localhost:8765`).
- `pip install stigmem-node` (for the CLI tools).
- An API key with `write` scope — set `STIGMEM_API_KEY` in your shell.
- Your existing instruction files in a directory (`./instructions/`).

---

## Step 1 — Inventory your instruction files

Before migrating, understand what you have. Run a preview (no writes):

```bash
stigmem instruction migrate ./instructions/ \
  --role backend-engineer \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --dry-run
```

Sample output:

```
=== Migration Preview ===
Path:    instructions
Scope:   role:backend-engineer  agent:a1b2c3d4-0000-0000-0000-000000000001
Version: v1

Facts: 11 create, 0 update, 0 noop, 0 tombstone
Total eager tokens: 1,129

  [+] agents                         234t   triggers: agents, cto, founding, engineer
  [+] what-you-own                   117t   triggers: architecture, delivery, ci, repo
  [+] what-you-hand-off-or-escalate   85t   triggers: escalate, product, ux, security
  [+] safety                         104t   triggers: safety, destructive, permission
  [+] references                      65t   triggers: references, load
  [+] heartbeat-checklist             41t   triggers: heartbeat, paperclip
  [+] work-standards                 162t   triggers: commit, bug, done, task
  [+] exit                            88t   triggers: exit, comment, before, exiting
  [+] soul-philosophy                   9t   triggers: soul, philosophy
  [+] technical-lenses               198t   triggers: reversibility, boring, yagni
  [+] tools                           26t   triggers: tools, stack

Dry-run mode — no changes written.
```

Study this table. For each chunk, ask:

- **Are the triggers right?** Do the keywords match what an agent or user would actually type when they need this chunk?
- **Is the description informative?** The description is used in semantic search. "Exit checklist" is better than "exit".
- **Is the chunk size appropriate?** Chunks under 20 tokens add manifest overhead without payoff. Chunks over 600 tokens may need splitting.

---

## Step 2 — Fix trigger keywords before migrating

The most common failure in lazy discovery rollouts is **narrow trigger keywords**. Both production rollouts hit the same issue: a chunk that is clearly needed on a given turn was missed because its keywords were written in internal-doc vocabulary rather than natural-language task intents.

### Example: exit/wrap-up chunks

The `exit` chunk in the backend-engineer instruction set had these initial triggers:

```json
"keywords": ["exit", "comment", "before", "exiting", "assignments", "valid", "mention"]
```

The chunk describes what the agent must do at end-of-turn. But when the agent's task intent is "implement a feature" or "review a PR", none of those exit keywords appear. Result: the chunk misses recall on every standard-task turn.

**Fix — add completion synonyms:**

```json
"keywords": [
  "exit", "wrap", "done", "complete", "finish",
  "final", "closing", "conclude", "end", "post update"
]
```

After this fix, the exit chunk surfaced on all standard-task turns with no further changes.

### Example: work-standards chunks

A `work-standards` chunk (code review standards, commit discipline) had these initial triggers:

```json
"keywords": ["commit", "bug", "done", "task", "work", "standards"]
```

A code-review turn's intent — "review pull request implementation" — contains none of those words. Result: the chunk misses on every code-review intent.

**Fix — add task-verb synonyms:**

```json
"keywords": [
  "commit", "review", "code", "implement", "test",
  "bug", "fix", "refactor", "pr", "pull request", "done", "task"
]
```

**Rule of thumb:** for any chunk that should be loaded during a category of work, include all common verbs for that work type.

### Edit the manifest directly or edit source files?

If you have not yet migrated, the cleanest path is to edit your source markdown files now — add a `<!-- triggers: ... -->` comment block under the heading, or simply use the `--triggers-file` option to supply a JSON overrides file:

```bash
# triggers-overrides.json
{
  "exit": {
    "keywords": ["exit", "wrap", "done", "complete", "finish", "final", "closing", "conclude"]
  },
  "work-standards": {
    "keywords": ["commit", "review", "code", "implement", "test", "bug", "fix", "done"]
  }
}
```

```bash
stigmem instruction migrate ./instructions/ \
  --role backend-engineer \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --triggers-file ./triggers-overrides.json \
  --dry-run
```

If you have already migrated and want to update triggers without changing content, use `stigmem instruction manifest edit`:

```bash
stigmem instruction manifest edit \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --chunk exit \
  --add-keywords "wrap,done,complete,finish,final,closing,conclude"
```

---

## Step 3 — Migrate

Run the migration with your corrected triggers. Confirm when prompted:

```bash
stigmem instruction migrate ./instructions/ \
  --role backend-engineer \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --triggers-file ./triggers-overrides.json
```

```
=== Migration Preview ===
…
Facts: 11 create, 0 update, 0 noop, 0 tombstone

Proceed? [y/N] y

  [CREATE] agents ✓
  [CREATE] what-you-own ✓
  [CREATE] work-standards ✓  (triggers patched)
  [CREATE] exit ✓            (triggers patched)
  …
Done. 11 fact(s) written, manifest published as version 'v1-1746393600'.
```

---

## Step 4 — Generate and inspect the boot stub

```bash
stigmem instruction boot-stub \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --role backend-engineer \
  --max-chunks 4 \
  --mode shadow \
  --output ./instructions/boot_stub.md
```

The generated stub:

```yaml
---
stub_version: 2
migration_mode: shadow
agent_id: a1b2c3d4-0000-0000-0000-000000000001
role: backend-engineer
manifest_path: ./instructions/manifest.json
max_chunks: 4
recall_tool: recall_instruction
---

You are a backend-engineer agent. Your full role specification, work
standards, and heartbeat procedure are loaded on demand via
`recall_instruction`. Check the manifest at `./instructions/manifest.json`
for available instruction chunks.

heartbeat_contract: "Before exiting any turn, call recall_instruction with
intent 'exit checklist' to load the turn-end procedure."
```

:::warning Start in `shadow` mode
`migration_mode: shadow` loads both the eager set and the lazy-recall set every turn. This lets you compare coverage and token delta without changing agent behavior. **Do not flip to `lazy` until the shadow audit passes.**
:::

---

## Step 5 — Run the shadow audit

Point your agent at `boot_stub.md` (instead of the eager instruction files) and run at least 10 representative turns. The shadow audit logs per-turn coverage automatically.

After your turns, check the audit:

```bash
stigmem instruction audit \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --format table
```

### Example: backend-engineer agent (11 chunks, 1 129t eager)

| Turn | Intent type | Lazy tokens | % baseline | Coverage | Regressions |
|------|-------------|-------------|------------|----------|-------------|
| 1 | Setup/migration | 310t | 27.5% | 100% | 0 |
| 2 | Task-execution | 525t | 46.5% | 100% | 0 |
| 3 | Code review | 565t | 50.0% | 100% | 0 |
| 4 | Bug fix/incident | 457t | 40.5% | 100% | 0 |
| 5 | Architecture decision | 565t | 50.0% | 100% | 0 |
| 6 | CI/CD pipeline | 457t | 40.5% | 100% | 0 |
| 7 | Security audit | 457t | 40.5% | 100% | 0 |
| 8 | Data model | 565t | 50.0% | 100% | 0 |
| 9 | Performance | 565t | 50.0% | 100% | 0 |
| 10 | Hiring/team | 493t | 43.7% | 100% | 0 |
| **Median** | | **525t** | **46.5%** | **100%** | **0** |

This agent's instruction set is compact (1 129t eager), so the token-budget target is ≤ 50% rather than the < 25% target used for larger sets. See [Lazy Instructions — token budget planning](./lazy-instructions#token-budget-planning) for calibration guidance.

### Example: project-manager agent (23 chunks, 3 190t eager)

| Turn | Intent type | Lazy tokens | % baseline | Coverage | Regressions |
|------|-------------|-------------|------------|----------|-------------|
| 1 | Setup/migration | 769t | 24.1% | 60% | 0 |
| 2 | Task-execution | 383t | 12.0% | 67% | 0 |
| 3 | Audit-review | 548t | 17.2% | 67% | 0 |
| 4 | Progress-review | 415t | **13.0%** | **100%** | 0 |
| 5–14 | Various | 415t | **13.0%** | **100%** | 0 |
| **Median (turns 4–14)** | | **415t** | **13.0%** | **100%** | **0** |

Turns 1–3 had 60–67% coverage. The root cause was a keyword gap in the exit chunk (described in Step 2 above). After the fix at turn 3 and bumping `max_chunks` from 3 to 4 at turn 4, the next **11 consecutive turns all hit 100% coverage at 13% of the eager baseline**.

### Interpreting the audit

**Coverage < 95%:** Inspect which chunks were missed. Run:

```bash
stigmem instruction audit \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --turn 3 \
  --show-missed
```

```
Turn 3 missed chunks:
  - exit (88t)  → triggered by: exit, comment, before, exiting
    Intent was: "review a pull request"
    Suggestion: add keywords: wrap, done, complete, review, code
```

Add the suggested keywords and re-run the next turn. You do not need to restart the shadow audit; the new triggers take effect on the next recall call.

**Token budget too high:** If your agent's median lazy load is > 25% of eager (for large sets) or > 50% (for small sets), check whether any chunk is set to `task_types: ["any"]` unnecessarily. That flag forces the chunk into every turn regardless of relevance.

**Regressions:** A regression is a turn where the agent needed information that would have been in the eager set but was not recalled. Regressions require immediate keyword fixes — do not flip until regressions reach 0.

---

## Step 6 — Flip to lazy

Once the shadow audit passes all three criteria, flip the boot stub:

```bash
stigmem instruction boot-stub \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --mode lazy \
  --output ./instructions/boot_stub.md
```

Or edit `boot_stub.md` directly:

```yaml
migration_mode: lazy   # was: shadow
```

Point your agent configuration at the boot stub. From this turn on, only the boot stub and manifest are loaded at startup. Everything else is loaded on demand via `recall_instruction`.

:::tip Keep eager files for 4 weeks
Retain your original instruction files for at least 4 weeks after flipping. This gives you a one-step rollback path: copy the eager files back to the harness entry-point and set `migration_mode: eager` in the boot stub.
:::

---

## Step 7 — Measure token-budget impact

After flipping, confirm the savings are holding in production:

```bash
stigmem instruction audit \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --since 2026-05-01 \
  --format summary
```

```
Shadow audit closed. Production (lazy) mode: 14 turns.

Token reduction:    87%  (3,190t → 415t per turn)
Coverage (14 turns): 100%
Regressions:          0

Savings so far:     ~38,150 tokens across 14 turns
```

---

## Troubleshooting

### The exit/wrap-up chunk is never recalled

Add the full completion synonym set to `load_triggers.keywords`:

```
wrap, done, complete, finish, final, closing, conclude, end, post update
```

This was the single most common coverage gap in both production rollouts. See [Step 2](#step-2--fix-trigger-keywords-before-migrating).

### Coverage is 100% but token budget is high

Check for:
- `task_types: ["any"]` on chunks that should not load every turn.
- `max_chunks` set too high (> 5). Each extra slot adds the next-best-scoring chunk even when it is not needed.

### `recall_instruction` returns empty `chunks`

This usually means the intent query is too short. The minimum effective query is 5–10 words. Check the agent's `recall_instruction` call and confirm it is sending the full turn context, not a one-word topic.

### Rollback

To rollback to eager loading:

1. Set `migration_mode: eager` in `boot_stub.md`.
2. Copy your original instruction files back to the harness entry point.
3. Restart the agent.

No database changes are needed — the Stigmem facts and manifest remain intact.

---

## What to read next

- [Lazy Instructions guide](./lazy-instructions) — boot stub format, manifest schema, and trigger design reference
- [Instruction Migration guide](./instruction-migration) — full CLI reference for `stigmem instruction migrate`
- [Recall guide](../concepts/recall/) — the underlying §20.3 recall pipeline
