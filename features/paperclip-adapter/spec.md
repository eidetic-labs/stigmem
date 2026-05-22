# Paperclip Adapter Spec

The Paperclip adapter connects Paperclip-managed agent work to Stigmem by
reading context at heartbeat start and writing lifecycle facts during checkout,
block, completion, delegation, and activity events.

## Surfaces

| Surface | Behavior |
| --- | --- |
| `skill.md` | Company skill content that instructs Paperclip agents how to read and write Stigmem facts. |
| `emit-fact.js` | Node CLI helper for `assert`, `query`, and `retract` operations against the Stigmem HTTP API. |
| `hook.sh` | Shell hook for checkout, completion, blocked, and post-tool-use heartbeat events. |
| `concept.md` | Setup and connector guidance for Paperclip and Claude Code usage. |
| `concept-federation.md` | Federation-oriented deployment guidance for Paperclip agent fleets. |

## Lifecycle Relations

| Relation | Scope | Producer |
| --- | --- | --- |
| `paperclip:checkout` | `company` | Agent or hook on task checkout. |
| `paperclip:issue_status` | `company` | Agent or hook on blocked or complete transitions. |
| `paperclip:blocked_by` | `company` | Agent or hook when an issue is blocked by another issue. |
| `paperclip:last_active` | `local` | `hook.sh post_tool_use` heartbeat. |
| `roadmap:decision` | `company` | Agent when recording a plan or architecture decision. |
| `intent:handoff_to` | `company` | Agent before delegating work. |
| `intent:context_ref` | `company` | Agent before delegating context to another worker. |

## Runtime Configuration

| Setting | Purpose |
| --- | --- |
| `STIGMEM_URL` | Required by `emit-fact.js`; points at the Stigmem API. |
| `STIGMEM_API_KEY` | Optional bearer token for Stigmem API calls. |
| `STIGMEM_SOURCE_ENTITY` | Source entity for asserted facts; defaults to `agent:unknown` in the hook. |
| `PAPERCLIP_TASK_ID` | Optional task id used by hook-generated issue facts. |

## Behavior

- At heartbeat start, agents should query relevant company, project, and
  handoff facts.
- On checkout, agents or hooks assert `paperclip:checkout` against
  `issue:<task-id>`.
- On blocked or completed transitions, agents or hooks assert
  `paperclip:issue_status`.
- On blocker transitions, agents may assert `paperclip:blocked_by` with a
  reference to the blocking issue.
- On post-tool-use events, the hook asserts `paperclip:last_active` with local
  scope when `PAPERCLIP_TASK_ID` is present.
- Delegation guidance records `intent:handoff_to` and `intent:context_ref`
  before posting the Paperclip delegation comment.

## Out of Scope

- Running or orchestrating Paperclip agents.
- Replacing Paperclip task state.
- Federation policy beyond the existing integration guide.
- Shipping this adapter in the default alpha artifact set before validation
  gates complete.

## Spec Assignment

There is no Spec-X assignment for the Paperclip adapter. It is an experimental
external adapter surface that uses registered relation namespaces and the
adapter ABI concepts, but does not define a standalone protocol feature.
