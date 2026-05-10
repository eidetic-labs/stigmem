# Architecture Decision Records (ADRs)

> Reference document. Drop in at `docs/adr/README.md`.

## What is an ADR?

**ADR** stands for **Architecture Decision Record** (sometimes "Architectural Decision Record" — the terms are interchangeable).

An ADR is a short, dated, immutable document that captures **a single significant decision**, why we made it, what alternatives we considered, and what the consequences are. ADRs live in the repo under `docs/adr/`, are numbered sequentially (`ADR-001`, `ADR-002`, ...), and form a versioned record of how the project's architecture evolved.

The format was popularized by Michael Nygard in a 2011 blog post and has become standard practice in infrastructure and platform projects.

## Why we use them

Three concrete reasons:

1. **Decisions get re-litigated constantly.** Six months from now, someone — possibly the original author — will ask "why did we move tombstones to experimental?" Without an ADR, the answer lives in chat history or memory. With an ADR, the answer is a versioned document with the reasoning intact.

2. **ADRs are a contract for scope discipline.** When `ADR-002` says "v1 critical-path scope is exactly this list," any proposal to add something not on the list has to either accept the constraint or write an amendment. The amendment requirement is productive friction.

3. **External adopters and contributors read them.** Threat models tell evaluators what we're worried about; ADRs tell them what we've decided and why. The combination is what credibility looks like in infrastructure projects.

## Standard structure

Every ADR follows the same template:

```markdown
# ADR-NNN: Short noun phrase

**Status:** Proposed | Accepted | Superseded by ADR-NNN | Deprecated
**Date:** YYYY-MM-DD
**Authors:** name(s)
**Supersedes:** (if applicable) ADR-NNN
**Related:** (if applicable) ADR-NNN, links to other artifacts

## Context

What is the situation? What forces are at play? Why are we deciding this now?
Be specific. Name the constraints, the prior art, the deadline if there is one.

## Decision

The call we made, in active voice. "We will..."
Be specific. "We will use a federated architecture" is a slogan, not a decision.
"We will use mTLS-default federation with capability tokens scoped to
verb+object pairs" is a decision.

## Alternatives considered

What else did we look at, and why didn't we pick it?
This section is the institutional memory; future maintainers will thank you.

## Consequences

What becomes easier? What becomes harder? What new risks emerge?
Be honest about the costs. ADRs that only list benefits are marketing docs.
```

## Rules

1. **ADRs are immutable after acceptance.** When circumstances change, write a new ADR that supersedes the old one. Don't edit an accepted ADR — that breaks the institutional memory the format exists to preserve.

2. **One decision per ADR.** Two related decisions get two ADRs that reference each other.

3. **Specific over abstract.** ADRs that describe a *concrete* decision survive contact with implementation. ADRs that describe a *direction* don't.

4. **Numbered sequentially, never reused.** If `ADR-005` is rejected, the number is still retired. Future ADRs are `ADR-006` onwards.

5. **Status changes are themselves a decision.** When an ADR moves from `Accepted` to `Superseded`, the new ADR captures that change with a `Supersedes:` reference.

6. **Approval: two contributors or the founder alone.** Sign-off on an ADR, an ADR amendment, or a PR through Phase B requires either two contributors *or* the founder alone. Founder solo-approval exists because the project has a small team and one contributor's unavailability would otherwise stop work. When the founder signs off alone, they take responsibility for the validation discipline that two-person review otherwise provides. See ADR-001 § *Contributor approval rule* for the full statement.

## Lifecycle

```
Proposed → discussion/review → Accepted → (later) Superseded by ADR-NNN
 ↘ (rare) Deprecated
```

Most ADRs are merged in `Accepted` status after pair review. `Proposed` is used when a decision is in flight and not yet committed; this is a useful state for getting feedback before locking in.

## When to write an ADR

Write one when a decision satisfies any of:

- **Has architectural blast radius** — affects more than one module, surface, or team.
- **Is non-obvious** — a future reader might reasonably ask "why did they do it this way?"
- **Has alternatives** — there was a real choice between two or more options.
- **Affects external contracts** — wire format, API surface, security model, deployment story.
- **Closes a documented gap** — resolves a specific issue from an audit, threat model, or operator report.

Don't write one for routine implementation choices ("we used a Python `dict` here"), library version bumps, or bug fixes.

## Cross-references

Stigmem ADRs frequently reference:

- The [threat model](../../spec/security/threat-model.md) — for security decisions.
- The [strengthening plan](../plans/strengthening-plan.md) — for delivery-timeline decisions.
- Audit findings (e.g., `stigmem/openclaw/audit.md`) — for ADRs that close specific issues.
- Other ADRs — for decisions that build on or supersede earlier ones.

When referencing, use relative links from the ADR's location.

## Index

The index is maintained at [`docs/adr/README.md`](README.md) (this file). Each ADR is listed with its number, title, status, and date. Add new ADRs to the table when accepted.

| # | Title | Status | Date |
|---|---|---|---|
| ADR-001 | Versioning, phases, and stability commitments | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-002 | v1 critical-path scope | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-003 | Capability-based prompt-injection handling | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-004 | Federation observability and incident response | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-005 | Documentation information architecture | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-006 | Batch-assert API for transactional multi-fact writes | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-007 | Argon2id migration for API key hashing | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-008 | Re-introduction gates for v2.0.0-experimental features | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-009 | Repository structure and execution flow | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-010 | Modular per-topic specs with independent versioning | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-011 | Plugin architecture for cross-cutting features (C1) | Accepted (@offbyonce, 2026-05-07) | 2026-05-07 |
| ADR-012 | Version-aware feature exposure | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-013 | Deprecation policy | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-014 | Compatibility matrix | Accepted (@offbyonce, 2026-05-07) | 2026-05-06 |
| ADR-015 | Adversarial conformance corpus and model certification framework | Accepted (@offbyonce, 2026-05-07) | 2026-05-07 |
| ADR-016 | Storage immutability enforcement | Accepted (@offbyonce, 2026-05-07) | 2026-05-07 |
| ADR-017 | Amendment to ADR-011 — CIDs as core (not plugin) | Accepted (@offbyonce, 2026-05-07) | 2026-05-07 |
| ADR-018 | Per-feature security documentation colocation | Accepted (@offbyonce, 2026-05-07) | 2026-05-07 |
| ADR-019 | Amendment to ADR-001 — adopt PEP 440 / semver alpha-beta-rc convention; per-ecosystem spelling; surface manifest delegation | Accepted (@offbyonce, 2026-05-08) | 2026-05-08 |

---

*Reference: Michael Nygard, "Documenting Architecture Decisions" (2011). The
format has been refined by many open-source projects; we use the
standard five-section variant with a sixth "Alternatives considered"
section because it materially improves institutional memory.*
