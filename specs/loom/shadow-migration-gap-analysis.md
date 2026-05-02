# Shadow Migration — Gap Analysis

**Source:** CTO `MEMORY.md` (4 project memory files + index)  
**Target:** Loom prototype node (`specs/loom/prototype/`)  
**Method:** Manual inspection + `seed_memory.py` script  
**Date:** 2026-05-01  
**Status:** Markdown stays source of truth; prototype is parallel write target.

---

## What Migrated Cleanly

| Memory shape | Loom translation | Notes |
|---|---|---|
| Scalar string facts ("Acme role = agent platform") | `(entity, relation, {type:string,v:...})` | Trivial. Clean fit. |
| Boolean flags ("in-house compliance = false") | `{type:boolean,v:false}` | Clean. |
| Status fields ("roadmap:v3 = dead") | `relation="roadmap:status", value={type:string,...}` | Clean. |
| Enumerated historical states (dead v1/v2/v3) | Low-confidence facts with `confidence=1.0` + value | The "low confidence" framing is wrong: these are *certain* facts about past state. The v0.1 spec conflates "how confident are we in this value?" with "is this fact still active?" — see Gap #3. |
| Friction items (7 numbered frictions) | Separate entities `loom:friction:1..7` each with a `friction:description` relation | Works but feels verbose. A list-value type would be cleaner (Gap #1). |

---

## Gaps Found

### Gap 1 — No list/array value type

**Memory shape:** "Seven frictions Loom solves: [1, 2, 3, 4, 5, 6, 7]"  
**Current mapping:** Seven separate facts, one per friction.  
**Problem:** Relationship between items is implicit (naming convention `loom:friction:N`). Query pattern `entity=loom:friction:*` relies on glob matching the prototype doesn't support. Callers must know the count and naming scheme to reconstruct the list.  
**Candidate fix:** Add `{ type: "list", v: string[] }` as a FactValue type, or add a `loom:member` relation pattern for ordered sets.

---

### Gap 2 — No document / rich-text value type

**Memory shape:** Memory files contain multi-paragraph markdown bodies — the full roadmap narrative, the design decisions log, etc.  
**Current mapping:** Can only store single-line strings. Long narrative content is truncated or flattened.  
**Problem:** The most information-dense parts of memory (rationale, meeting notes, design decisions) don't fit the atomic fact shape without a `document` reference type.  
**Candidate fix:** Add `{ type: "ref", v: "<content-store-URI>" }` with a separate content store, or add `{ type: "text", v: string }` (unbounded string) and accept that atomic fact ≠ short fact.

---

### Gap 3 — Confidence doesn't distinguish "certainty" from "recency/validity"

**Memory shape:** Dead roadmaps (v1/v2/v3) — certain facts about past state. The CTO is 100% confident they're dead; the facts are just *historical*, not uncertain.  
**Current mapping:** Written with `confidence=1.0` (certain) and value `"dead"`. This is accurate but loses the temporal framing.  
**Problem:** A caller querying all roadmap statuses gets v3="dead" and v4="active" with equal confidence. There's no way to express "this was true at time T but superseded at time T+1" without a `loom:superseded_by` relation convention that the spec doesn't define.  
**Candidate fix:** Add a `superseded_by` fact relation as a first-class spec element, or add `valid_until` as an optional field alongside `timestamp`.

---

### Gap 4 — No structured relationship type (entity → entity links)

**Memory shape:** "Any commercial or technical commitment between Acme and Giganomix must go to the board."  
**Current mapping:** This is a *policy* about two entities, not a fact about one entity. There's no natural primary entity to attach it to — it's a relationship between `company:acme` and `company:giganomix` that also involves `entity:board`.  
**Problem:** The current `(entity, relation, value)` shape assumes one primary entity and one atomic value. N-ary relationships (A relates to B with condition C) require either (a) a reification entity or (b) a value type that can encode references to multiple entities.  
**Candidate fix:** Allow `value = { type: "ref", v: URI }` to point to another entity, and allow a fact's `entity` to be a tuple URI like `loom:edge:acme:giganomix` (reification). The spec should clarify the canonical pattern.

---

### Gap 5 — No memory-type metadata (user vs. project vs. feedback vs. reference)

**Memory shape:** Files carry YAML frontmatter with `type: project | user | feedback | reference`.  
**Current mapping:** This type is lost. All facts flatten into the same namespace.  
**Problem:** Memory types carry different retention and trust semantics — feedback memories are behavioral rules, reference memories are external pointers. Downstream agents querying the fabric can't filter by memory type without a convention.  
**Candidate fix:** Add `relation="memory:type"` as a standard relation with values like `"project" | "user" | "feedback" | "reference"`. Or add `scope` subcategories. Or leave to convention and document it in the spec.

---

### Gap 6 — Decay semantics for "deprecated but true" vs. "uncertain" are conflated

**Memory shape:** "v3 roadmap was flagged dead on 2026-05-02 (ACM-18 comment ff95e2af)."  
**Current mapping:** A confidence=1.0 fact with `value="dead"` plus a `source` pointing at the CTO. The *event* that caused the status change (the board comment) is in the memory text but not representable as a first-class fact linkage.  
**Problem:** The prototype can store "v3 is dead" but cannot store "v3 was marked dead because of event X at time T." Audit trail is flat.  
**Candidate fix:** Allow an optional `caused_by` fact field that points to an event URI or another fact ID. This is a form of provenance chaining.

---

## Summary: 6 Gaps

| # | Gap | Severity | Candidate fix |
|---|-----|----------|---------------|
| 1 | No list/array value type | Medium | `{type:"list"}` or `loom:member` relation |
| 2 | No document/rich-text type | High | `{type:"ref"}` + content store, or unbounded text |
| 3 | Confidence ≠ validity/recency | Medium | `superseded_by` relation or `valid_until` field |
| 4 | N-ary relationships not modeled | High | Reification pattern + `{type:"ref"}` for values |
| 5 | Memory-type metadata lost | Low | `memory:type` standard relation |
| 6 | Event-driven audit trail not modeled | Medium | `caused_by` optional field |

**Severity legend:** High = spec needs to address before Phase 1 RFC. Medium = Phase 2 is acceptable. Low = can be left to convention.

---

## Recommendation

Gaps 2 and 4 are the most structurally significant — rich text and N-ary
relationships come up immediately when migrating even a small, real-world
memory corpus. The v0.1 spec should at minimum acknowledge these two gaps
and provide a canonical workaround pattern, even if the full fix is Phase 2.

Gaps 1, 3, 6 are related to temporal/versioning semantics — they cluster
around the question "how does Loom represent change over time?" This should
become a dedicated section in the v0.1 spec before the Phase 1 RFC.

Gap 5 (memory type metadata) is the easiest: it can be addressed by
documenting a standard `loom:memory:type` relation in the spec with no
schema change needed.
