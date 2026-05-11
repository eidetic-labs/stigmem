---
title: Instruction Migration
sidebar_label: Instruction Migration
description: Use stigmem instruction migrate to publish markdown instruction files as atomic facts and a lazy-loaded manifest.
audience: Integrator
---

# Instruction Migration

**Audience:** Agent operators and system integrators publishing instruction files to a Stigmem node.  
**Spec reference:** §21 (pre-reset instruction-discovery design).

---

The `stigmem instruction migrate` command converts a directory (or single file) of markdown instruction files into atomic Stigmem facts and publishes a lazy-loaded manifest so agents can recall specific instruction units on demand instead of loading all instructions at boot.

## How it works

1. **Parse** — each `.md` file is split on H1/H2/H3 headings into one _instruction unit_ per section (one unit per file when no headings are present). YAML frontmatter is stripped.
2. **Diff** — each unit is compared against the current state in the node (via HTTP or local DB). Actions: `CREATE`, `UPDATE`, `NOOP`, or `TOMBSTONE`.
3. **Preview** — the diff is printed. With `--dry-run`, execution stops here.
4. **Write** — `CREATE` and `UPDATE` units are posted to `/v1/facts` with relation `instruction:content` and scope `local`.
5. **Publish manifest** — a new manifest is `PUT` to `/v1/agents/{agent_id}/instruction-manifest` listing every live unit with its load triggers and token estimate.

## Prerequisites

- A running Stigmem node (default `http://127.0.0.1:8000`).
- An API key with `write` scope — set via `--api-key` or the `STIGMEM_API_KEY` env var.
- Python package: `pip install stigmem-node` (includes `httpx` for HTTP transport).

## Quick start

```bash
# 1. Preview the migration (no writes)
stigmem instruction migrate ./instructions/ \
  --role cto \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --dry-run

# 2. Run the migration (interactive confirmation)
stigmem instruction migrate ./instructions/ \
  --role cto \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001

# 3. Verify a unit was loaded correctly
curl -s -X POST http://127.0.0.1:8000/v1/agents/a1b2c3d4-0000-0000-0000-000000000001/recall-instruction \
  -H 'Authorization: Bearer $STIGMEM_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{"intent": "deployment checklist", "max_chunks": 3}'
```

---

## CLI reference — `stigmem instruction migrate`

```
stigmem instruction migrate PATH [options]
```

### Positional

| Argument | Description |
|----------|-------------|
| `PATH` | Markdown file or directory to migrate. Directories are scanned for `*.md` files recursively. |

### Scope (one required)

| Flag | Description |
|------|-------------|
| `--role ROLE` | Agent role name (e.g. `cto`). Facts are scoped to `instruction:{deployment}/agent/{agent_id}/{slug}/{version}`. |
| `--skill SKILL` | Skill name (e.g. `paperclip`). Facts are scoped to `instruction:{deployment}/skill/{skill_name}/{slug}/{version}`. |

`--role` and `--skill` are mutually exclusive.

### Required

| Flag | Description |
|------|-------------|
| `--agent-id AGENT_ID` | Agent UUID that owns the manifest. |

### Optional

| Flag | Default | Description |
|------|---------|-------------|
| `--deployment NAME` | `default` | Deployment namespace used in the fact URI. |
| `--version VER` | `v1` | Fact version string appended to each URI. |
| `--node-url URL` | `http://127.0.0.1:8000` | Stigmem node base URL. |
| `--api-key KEY` | `$STIGMEM_API_KEY` | API key for writing facts and publishing the manifest. Read-only fallback to env var. |
| `--db PATH` | — | Path to a local `stigmem.db` SQLite file. When set, idempotency checks query the local DB instead of making HTTP fact queries, which is faster for local deployments. |
| `--dry-run` | — | Print the migration preview and exit without writing anything. |
| `-y`, `--yes` | — | Skip the interactive confirmation prompt. |

---

## Fact URI scheme

Each instruction unit is stored as a fact whose `entity` is a structured URI:

**Role-scoped:**
```
instruction:{deployment}/agent/{agent_id}/{slug}/{version}
# e.g. instruction:default/agent/a1b2c3d4.../deployment-checklist/v1
```

**Skill-scoped:**
```
instruction:{deployment}/skill/{skill_name}/{slug}/{version}
# e.g. instruction:default/skill/paperclip/setup-instructions/v1
```

The `slug` is derived from the heading text: lowercased, non-alphanumeric runs replaced by `-`, truncated to avoid collisions. When duplicate slugs arise across files, the file stem is prepended automatically.

---

## Idempotency semantics

Running `stigmem instruction migrate` against the same directory twice is safe. The tool computes a diff before writing anything:

| Action | Condition | Result |
|--------|-----------|--------|
| `CREATE` | No existing fact for this URI | New fact posted to `/v1/facts` |
| `UPDATE` | Existing fact content differs from new content (byte comparison) | New fact version posted |
| `NOOP` | Existing fact content is identical | Skipped; no write issued |
| `TOMBSTONE` | Unit was in the previous manifest but is absent from the new file set | Manifest entry removed; underlying fact **kept** in the DB for audit history |

The manifest is only published if all `CREATE`/`UPDATE` writes succeed. A partial write aborts manifest publication, so the old manifest remains active.

:::tip No accidental rewrites
`NOOP` entries generate zero HTTP requests. Running the same migration ten times costs the same as running it once — only changed or new content triggers writes.
:::

---

## Tombstone behavior

When a heading or file is removed between migration runs, the missing unit becomes a `TOMBSTONE`:

- The manifest entry for that unit is **removed**, so agents no longer load it via `recall-instruction`.
- The underlying `instruction:content` fact is **preserved** in the database. Nothing is deleted.
- The preview report lists tombstones as `[T] unit-name (removed — existing facts kept for history)`.

This means you can always recover or audit old instruction content by querying the facts API directly, even after a tombstone run.

---

## Dry-run → confirm → recall-instruction round-trip

The recommended workflow is: preview → inspect → confirm → verify.

### Step 1 — Preview the diff

```bash
stigmem instruction migrate ./agents/cto/instructions/ \
  --role cto \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --dry-run
```

Sample output:

```
=== Migration Preview ===
Path:    agents/cto/instructions
Scope:   role:cto  agent:a1b2c3d4-0000-0000-0000-000000000001
Version: v1

Facts: 2 create, 1 update, 3 noop, 0 tombstone

  [+] deployment-checklist
       URI:    instruction:default/agent/a1b2c3d4.../deployment-checklist/v1
       tokens: ~340

  [~] incident-response
       URI:    instruction:default/agent/a1b2c3d4.../incident-response/v1
       tokens: ~210
       lines:  18 → 22

  [=] code-review-standards
  [=] security-posture
  [=] on-call-runbook

Dry-run mode — no changes written.
```

### Step 2 — Confirm and write

```bash
stigmem instruction migrate ./agents/cto/instructions/ \
  --role cto \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001
# Prints the same preview, then prompts:
# Proceed? [y/N] y
#   [CREATE] deployment-checklist ✓
#   [UPDATE] incident-response ✓
# Done. 2 fact(s) written, manifest published as version 'v1-1746393600'.
```

Use `-y` / `--yes` in CI pipelines to skip the prompt.

### Step 3 — Verify with recall-instruction

```bash
curl -s -X POST \
  http://127.0.0.1:8000/v1/agents/a1b2c3d4-0000-0000-0000-000000000001/recall-instruction \
  -H 'Authorization: Bearer $STIGMEM_API_KEY' \
  -H 'Content-Type: application/json' \
  -d '{
    "intent": "how do I handle a production incident?",
    "max_chunks": 3,
    "token_budget": 2000
  }'
```

Expected response shape:

```json
{
  "chunks": [
    {
      "name": "incident-response",
      "fact_uri": "instruction:default/agent/a1b2c3d4.../incident-response/v1",
      "content": "## Incident Response\n\nWhen a production incident...",
      "tokens": 210,
      "score": 0.91,
      "source": "stigmem"
    }
  ],
  "total_tokens": 210,
  "truncated": false,
  "missed_hints": [],
  "audit_token": "aud_..."
}
```

The `audit_token` can be submitted to `POST /v1/instruction/audit` to record which chunks were actually used.

---

## Using a local DB for faster idempotency checks

In local deployments you can skip HTTP fact queries entirely by pointing the tool at your `stigmem.db` directly:

```bash
stigmem instruction migrate ./instructions/ \
  --role cto \
  --agent-id a1b2c3d4-0000-0000-0000-000000000001 \
  --db ./stigmem.db \
  --yes
```

The `--db` flag reads existing fact content and the previous manifest directly from SQLite. Writes still go to the node via HTTP.

---

## CI / automation example

```yaml
# .github/workflows/deploy-instructions.yml
- name: Migrate instruction files
  env:
    STIGMEM_API_KEY: ${{ secrets.STIGMEM_API_KEY }}
  run: |
    stigmem instruction migrate ./agents/cto/instructions/ \
      --role cto \
      --agent-id ${{ vars.CTO_AGENT_ID }} \
      --node-url ${{ vars.STIGMEM_NODE_URL }} \
      --yes
```

---

## Related guides

- [Recall](../concepts/recall/) — Hybrid recall pipeline for general fact retrieval
- [Asserting facts](../concepts/facts/asserting-facts) — Low-level fact write API
- [Agent keypairs](../security/agent-keypairs) — Ed25519 key registration for agent identity
- [Audit log](../security/audit-log) — End-to-end audit trail for fact writes
