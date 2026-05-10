# Stigmem — Paperclip Adapter Skill

Use this skill to read and write shared knowledge from/to the Stigmem node within a Paperclip heartbeat.

## When to use

- **On heartbeat start:** Query Stigmem for active project constraints, board preferences, and
  prior commitments relevant to the current task. Pull these into context before starting work.
- **On checkout:** Assert a `paperclip:checkout` fact capturing that you are working on the issue.
- **On plan change:** Assert a `roadmap:decision` fact capturing the decision and its rationale.
- **On task completion or blocking:** Assert a `paperclip:issue_status` fact.
- **On escalation:** Assert a `intent:escalation` fact before posting the Paperclip comment.

## Configuration

The following environment variables must be set in your agent's adapter config or shell:

| Variable | Description |
|---|---|
| `STIGMEM_URL` | Base URL of the Stigmem node, e.g. `http://localhost:8765` |
| `STIGMEM_API_KEY` | API key (omit if the node runs in `auth: none` mode) |
| `STIGMEM_SOURCE_ENTITY` | Your agent's entity URI, e.g. `agent:cto` |

## Reading context on heartbeat start

At the beginning of each heartbeat, query for relevant facts before doing any work:

```bash
# Pull active company-wide constraints and preferences
curl -sf "${STIGMEM_URL}/v1/facts?entity=company:acme&scope=company&min_confidence=0.7" \
  -H "Authorization: Bearer ${STIGMEM_API_KEY}" | jq '.facts[] | {relation, value}'

# Pull current project constraints
curl -sf "${STIGMEM_URL}/v1/facts?entity=project:${PROJECT_ID}&scope=company" \
  -H "Authorization: Bearer ${STIGMEM_API_KEY}" | jq '.facts[]'

# Pull board preferences relevant to your role
curl -sf "${STIGMEM_URL}/v1/facts?entity=agent:ceo&relation=preference:&scope=company" \
  -H "Authorization: Bearer ${STIGMEM_API_KEY}" | jq '.facts[]'
```

Or use the helper script:

```bash
node stigmem/adapters/paperclip/emit-fact.js query \
  --entity "project:${PROJECT_ID}" --scope company
```

## Writing facts during a heartbeat

### Issue checkout
```bash
node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "issue:${PAPERCLIP_TASK_ID}" \
  --relation "paperclip:checkout" \
  --value '{"type":"string","v":"in_progress"}' \
  --source "${STIGMEM_SOURCE_ENTITY}"
```

### Plan decision
```bash
node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "decision:${DECISION_SLUG}" \
  --relation "roadmap:decision" \
  --value '{"type":"text","v":"Chose SQLite for the v0.3 design window because ..."}' \
  --source "${STIGMEM_SOURCE_ENTITY}" \
  --scope company
```

### Blocker
```bash
node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "issue:${PAPERCLIP_TASK_ID}" \
  --relation "paperclip:blocked_by" \
  --value '{"type":"ref","v":"issue:'${BLOCKING_ISSUE_ID}'"}' \
  --source "${STIGMEM_SOURCE_ENTITY}"
```

### Issue complete
```bash
node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "issue:${PAPERCLIP_TASK_ID}" \
  --relation "paperclip:issue_status" \
  --value '{"type":"string","v":"done"}' \
  --source "${STIGMEM_SOURCE_ENTITY}"
```

## Scope guidance

| Fact type | Recommended scope |
|---|---|
| Board preferences, company constraints | `company` |
| Task-specific working notes | `local` |
| Cross-company protocol knowledge | `public` |
| Team-internal agreements | `team` |

## Delegation handoff

When handing off to a direct report, assert a handoff intent fact before posting
the Paperclip delegation comment. This ensures the receiving agent can pull context
from Stigmem without a manual re-brief:

```bash
node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "handoff:${PAPERCLIP_TASK_ID}" \
  --relation "intent:handoff_to" \
  --value '{"type":"ref","v":"agent:senior-engineer"}' \
  --source "${STIGMEM_SOURCE_ENTITY}" \
  --scope company

node stigmem/adapters/paperclip/emit-fact.js assert \
  --entity "handoff:${PAPERCLIP_TASK_ID}" \
  --relation "intent:context_ref" \
  --value '{"type":"ref","v":"issue:'${PAPERCLIP_TASK_ID}'"}' \
  --source "${STIGMEM_SOURCE_ENTITY}" \
  --scope company
```

The receiving agent should call the `query` command on startup to pull these handoff facts.

## Using the Python SDK

For richer use, install `stigmem-py` and use it directly:

```python
from stigmem import StigmemClient, string_value, text_value

client = StigmemClient(
    url=os.environ["STIGMEM_URL"],
    api_key=os.environ.get("STIGMEM_API_KEY"),
)

# Read context at heartbeat start
constraints = client.query(entity="company:acme", relation="roadmap:constraint", scope="company")

# Assert a decision
client.assert_fact(
    entity=f"decision:{decision_slug}",
    relation="roadmap:decision",
    value=text_value(rationale),
    source=os.environ["STIGMEM_SOURCE_ENTITY"],
    scope="company",
)
```
