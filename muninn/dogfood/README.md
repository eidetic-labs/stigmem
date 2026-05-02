# Muninn Dogfood — CEO Memory Migration

Phase 2 validation: migrate the CEO's PARA-style `MEMORY.md` into a running Muninn node as Muninn facts.

## Quick start

```bash
# 1. Start the node
cd muninn/node
MUNINN_DB_PATH=./muninn.db muninn-node &

# 2. Run the migration (dry run first)
python muninn/dogfood/migrate_ceo_memory.py \
  --memory-dir ~/.claude/projects/<proj>/memory \
  --node-url http://localhost:8765 \
  --dry-run

# 3. Write for real
python muninn/dogfood/migrate_ceo_memory.py \
  --memory-dir ~/.claude/projects/<proj>/memory \
  --node-url http://localhost:8765

# 4. Verify directly
curl http://localhost:8765/v1/facts?entity=user:ceo | jq .
```

## Fact model

| Field      | Value                     |
|------------|---------------------------|
| entity     | `user:ceo`                |
| relation   | `memory:{type}` (type from frontmatter: project, feedback, user, reference) |
| value      | `{ type: "text", v: <full file body> }` |
| source     | `agent:muninn-migrator`   |
| scope      | `company`                 |
| confidence | `1.0`                     |

## Notes

- This is a **shadow write**: the Markdown files remain the source of truth.
- Phase 3 will evaluate switching the source-of-truth to Muninn.
- Re-running is safe: each run appends new facts (immutable fact model).
  Query with `source=agent:muninn-migrator` to identify migration-produced facts.
