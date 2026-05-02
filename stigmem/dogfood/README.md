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
