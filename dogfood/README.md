# Stigmem Dogfood — CEO Memory Migration

Phase 2 validation: migrate the CEO's PARA-style `MEMORY.md` into a running Stigmem node as Stigmem facts.

## Quick start

```bash
# 1. Start the node
cd stigmem/node
STIGMEM_DB_PATH=./stigmem.db stigmem-node &

# 2. Run the migration (dry run first)
python stigmem/dogfood/migrate_ceo_memory.py \
  --memory-dir ~/.claude/projects/<proj>/memory \
  --node-url http://localhost:8765 \
  --dry-run

# 3. Write for real
python stigmem/dogfood/migrate_ceo_memory.py \
  --memory-dir ~/.claude/projects/<proj>/memory \
  --node-url http://localhost:8765

# 4. Verify directly
curl http://localhost:8765/v1/facts?entity=user:ceo | jq .
```

## Fact model

| Field      | Value                     |
|------------|---------------------------|
| entity     | `user:ceo`                |
| relation   | `memory:{type}:{slug}` (type from frontmatter + filename slug for uniqueness) |
| value      | `{ type: "text", v: <full file body> }` |
| source     | `agent:stigmem-migrator`   |
| scope      | `company`                 |
| confidence | `1.0`                     |

## Notes

- This is a **shadow write**: the Markdown files remain the source of truth.
- Phase 3 will evaluate switching the source-of-truth to Stigmem.
- Re-running is safe: each run appends new facts (immutable fact model).
  Query with `source=agent:stigmem-migrator` to identify migration-produced facts.

---

## Snapshot — Contradiction Metrics

`snapshot.sh` emits a `## Contradiction Metrics` section at the end of each daily
snapshot.

### How it works

The script calls `GET /v1/conflicts?status=unresolved&limit=500` and
`GET /v1/conflicts?status=resolved&limit=500`, then groups results by scope using
`jq`.  Each conflict record includes `fact_a` and `fact_b` (the two competing
facts), and since a contradiction can only exist within a single scope, the scope
is read from `fact_a.scope` (falling back to `fact_b.scope` for data-integrity
safety).

### Output schema

```markdown
## Contradiction Metrics

| Scope   | Unresolved | Resolved | Total |
|---------|------------|----------|-------|
| company | 2          | 1        | 3     |
| team    | 0          | 4        | 4     |
```

| Column       | Type    | Description                                                       |
|--------------|---------|-------------------------------------------------------------------|
| `Scope`      | string  | Stigmem scope: `local`, `team`, `company`, or `public`           |
| `Unresolved` | integer | Open conflicts — facts that still contradict each other           |
| `Resolved`   | integer | Conflicts closed via `POST /v1/conflicts/{id}/resolve`            |
| `Total`      | integer | `Unresolved + Resolved` for the scope                            |

If no contradictions exist the section emits `_No contradictions detected._`
instead of the table.

If the server returns `has_more: true` (more than 500 conflicts in either bucket),
a blockquote warning is appended noting that the counts are a lower bound.

### Source endpoints

| Endpoint                          | Purpose                      |
|-----------------------------------|------------------------------|
| `GET /v1/conflicts?status=unresolved&limit=500` | Fetch open conflicts  |
| `GET /v1/conflicts?status=resolved&limit=500`   | Fetch closed conflicts |
