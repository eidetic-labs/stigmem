# Stigmem Relation Namespacing Convention

**Scope:** All fact writes to any Stigmem node.  
**Status:** Normative convention as of Phase 5 (ACM-50 Deliverable 5).  
**Companion spec:** §9 (Namespace Registry) + §2.6 (Entity Naming Rules).

---

## The Problem — Silent Relation Collisions (Bug 1)

Two agents writing semantically different facts under the same `(entity, relation)` tuple
create a contradiction where none should exist:

```
entity="stigmem://acme/project/acm-18"  relation="status"  value="in_progress"   source=agent:pm
entity="stigmem://acme/project/acm-18"  relation="status"  value="code_complete"  source=agent:cto
```

Both are valid facts about the same project. They differ semantically (project management
status vs engineering completion status), but Stigmem treats them as a contradiction
because they share `(entity, relation, scope)`. The node opens a conflict and every
downstream query sees contradicted results until a human intervenes.

The root cause is **semantic overloading** of the relation field.

---

## The Fix — Sub-relations

Each distinct semantic topic MUST have its own sub-relation. Use dot-separated
namespacing within your prefix:

| Bad (collision) | Good (distinct) |
|----------------|----------------|
| `status` | `pm:status`, `eng:status` |
| `memory:role` | `memory:role:primary`, `memory:role:acting` |
| `acme:phase` | `acme:phase:current`, `acme:phase:completed` |

**Rule:** If two different agents, or two different meanings, could ever write to
the same `(entity, relation)` tuple — it is NOT the same relation.

---

## Naming Rules for Relations

1. **Always namespace.** Never use bare words like `status`, `name`, `value`.
   Always prefix with your domain: `pm:status`, `eng:status`, `agent:memory:role`.

2. **Use dot-separated sub-relations for variants of the same concept.**
   `memory:role` for the canonical role, `memory:role:acting` for a temporary override.

3. **Facts with different lifecycles need different relations.**
   If one fact expires daily and another is permanent, they are different relations.

4. **Conflict-safe updates use timestamped sub-relations.**
   If two agents need to independently record versions of the same concept:
   ```
   relation="acme:phase:completed"  value="phase-3"
   relation="acme:phase:completed"  value="phase-4"
   ```
   Use `acme:phase:completed` (append-safe log) rather than `acme:phase` (overwrite intent).

5. **System relations (prefix `stigmem:`) are reserved.**
   Do not write facts with `relation` starting with `stigmem:` — these are spec-reserved.
   See §9.1 of the spec.

---

## Migration Guide — Resolving Existing Collisions

If you have silent collisions from informal or over-broad relations:

### Step 1 — Detect

Query with `include_contradicted=true` to find all contradicted facts:

```bash
curl "$STIGMEM_URL/v1/facts?entity=<entity>&include_contradicted=true"
# or use lint_scope:
curl "$STIGMEM_URL/v1/lint?scope=company"
```

The `lint_scope` tool surfaces all unresolved conflicts as `unresolved_conflict` issues.

### Step 2 — Understand semantics

For each conflict: are these two facts semantically the same thing (genuine contradiction)
or two different concepts that share a relation (collision)?

- **Genuine contradiction:** use `resolve_contradiction` to pick the winner.
- **Collision:** migrate to sub-relations (see Step 3).

### Step 3 — Migrate colliding facts

For each colliding pair, assert new facts under correctly namespaced relations,
then retract (`confidence=0.0`) the original colliding facts:

```python
# Old (collision):
# entity="acme/project", relation="status", value="in_progress"
# entity="acme/project", relation="status", value="code_complete"

# New (distinct sub-relations):
client.assert_fact("stigmem://acme/project/acm-18", "pm:status",  {"type": "string", "v": "in_progress"},   source="agent:pm")
client.assert_fact("stigmem://acme/project/acm-18", "eng:status", {"type": "string", "v": "code_complete"}, source="agent:cto")

# Retract originals (set confidence=0.0)
client.retract(old_fact_id_1)
client.retract(old_fact_id_2)
```

### Step 4 — Verify

Run `lint_scope` again to confirm no unresolved conflicts remain for the migrated entity.

---

## Write-time Collision Validator

Starting with Phase 5, the node emits a warning log entry when a new fact would
contradict an existing fact on `assert_fact`. This is surfaced via:

1. **The `contradicted: true` field** in the `assert_fact` response — check this
   in your agent to detect collisions immediately on write.
2. **`GET /v1/lint?scope=<scope>`** — run periodically to find accumulated collisions.

A future validator (Phase 6) will reject writes that violate declared unique-relation
constraints. For now, the caller is responsible for using correctly namespaced relations.

---

## Quick Reference

| Do | Don't |
|----|-------|
| `pm:status`, `eng:status` | `status` |
| `memory:role:primary` | `role` |
| `acme:decision:approved-at` | `approved` |
| `stigmem://company.acme/agent/cto` | `agent:cto` (informal) |
| Separate relations for separate lifecycles | One relation, multiple concurrent writers |

---

*Last updated: Phase 5 (ACM-50). Maintainer: CTO.*
