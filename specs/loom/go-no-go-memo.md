# Phase 0 Go / No-Go Memo — Loom
## From: CTO &nbsp;&nbsp;&nbsp; To: CEO &nbsp;&nbsp;&nbsp; Date: 2026-05-01 (Phase 0 week 2)

---

## Recommendation: **GO — commit to Phase 1 with sharpened scope**

Phase 0 validated the core bet. The six deliverables are complete. The spec,
prototype, gap analysis, peer landscape, and design-partner list all point to the
same conclusion: **the federated knowledge protocol niche is real, unoccupied, and
technically tractable**. There is no evidence that warrants a no-go.

---

## Evidence Summary

### D1 — Spec (loom-spec.md v0.2)
The atomic fact shape `(entity, relation, value, source, timestamp, valid_until,
confidence, scope)` survived real-world dogfooding with one schema iteration
(added `text` type, reification pattern, `valid_until` field). The intent
envelope schema is fully drafted. No show-stopper design problems found.

### D2 — Prototype
200-line FastAPI + SQLite node runs in a container. `assert(fact)` and
`query(pattern)` work. Contradiction detection works. Decay filtering works.
Prototype is discardable by design — it served its purpose.

### D3 — Shadow migration gap analysis
6 gaps found. 2 are high-severity and have been addressed in v0.2 of the spec.
The remaining 4 are medium/low and acceptable for Phase 2. No fundamental
contradiction of the fact-shape model was found.

### D4 — Design-partner candidates (no interviews yet — see Risk 2)
Three qualified candidates identified: Daniel Chalef (Zep), Charles Packer
(Letta), topoteretes/Cognee. All are public, technically aligned, and likely
open to conversation. Outreach is Phase 1 week 1.

### D5 — Peer landscape
Zep/Graphiti is the closest technical neighbor (temporal edges, open-source,
MCP server). No peer has shipped or specced a federated, cross-company knowledge
protocol. The gap is confirmed real. Competitive moat: open protocol with
federation semantics (ActivityPub/SMTP model), not just another memory store.

---

## Risks and Mitigations

| # | Risk | Likelihood | Mitigation |
|---|------|-----------|------------|
| 1 | Federation semantics turn out hard to standardize (network effects needed early) | Medium | Phase 1 focus: get 2–3 design partners to co-author the federation section before publishing. Don't publish alone. |
| 2 | Design-partner interviews not done yet | Low | Outreach planned for Phase 1 week 1. Phase 0 constraint (read public only) respected. Interviews are a Phase 1 input, not a Phase 0 blocker. |
| 3 | Auth gap (scope meaningless without identity) | Medium | Documented honestly in v0.2 §8. Phase 2 production-hardening track. Does not block the protocol design work in Phase 1. |
| 4 | Namespace collision in `loom:`, `rel:`, `memory:` namespaces | Low | Open question for Phase 1: define a governed namespace registry early. |
| 5 | Zep/Graphiti becomes a direct competitor (they ship federation first) | Low | Zep's model is a retrieval engine, not a protocol layer. Monitor their roadmap. Potential design-partner, not threat. |

---

## What Phase 1 Is

Phase 1 is the **public RFC**: publish `loom-spec.md` in a public GitHub repo,
invite design partners to co-author the federation section, run 3 interviews,
and publish a v0.3 spec that incorporates feedback. No production code.

### Phase 1 in-scope
- Open GitHub repo (`acme-co/loom` or preferred name) with spec + prototype
- 3 design-partner interviews + feedback incorporated
- v0.3 spec with: federation section (co-authored), auth stub, namespace registry plan
- Community RFC process bootstrapped (issue template, contribution guide)

### Phase 1 out of scope
- Production hardening of prototype
- Paperclip / OpenClaw / MCP adapters (Phase 4)
- Hosted offering, multi-tenancy, billing (Phase 7)
- Premature Paperclip or OpenClaw coordination (still holdco-level — do not publish
  publicly as "the Paperclip memory layer")

### Phase 1 success criterion
v0.3 spec published, ≥2 external contributors with pull requests merged, and
at least 1 design partner named as spec co-author.

---

## Budget ask

Phase 1 is spec + interview work + open-source scaffolding. CTO-hours only.
No new hires, no infra spend, no external contracts. Estimates a few days
of focused work over 2 weeks.

---

## Decision requested

**Approve Phase 1 commit.** CTO to proceed with opening the public repo and
kicking off design-partner outreach in the next sprint.

If CEO has concerns about coordination timing with Paperclip/OpenClaw leadership,
that should be resolved before the public repo goes live — raise as a board-level
call, not a blocker to internal Phase 1 prep.

---

*Prepared by CTO, Acme Corp. Source issue: [ACM-19](/ACM/issues/ACM-19).
Parent: [ACM-18](/ACM/issues/ACM-18).*
