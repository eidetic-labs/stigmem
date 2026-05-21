# Roadmap and Release Roadmap Standards

This document defines the required shape for `ROADMAP.md` and internal release
roadmaps. It prevents the roadmap from becoming either a vague strategy note or
an unwieldy execution checklist.

## Document Roles

| Document | Audience | Purpose | Must not become |
| --- | --- | --- | --- |
| `ROADMAP.md` | Public contributors, operators, maintainers | Strategic horizon, version-line sequencing, gates, and durable policy-aligned intent | A per-issue task board or release-notes draft |
| `docs/internal/releases/<version>-roadmap.md` | Maintainers and release owners | Detailed release contract for one version: scope, exclusions, artifacts, evidence gates, and release-note candidates | A replacement for GitHub issues or the changelog |
| GitHub milestone / issues | Maintainers and contributors | Live execution tracking for the active release | The only place where release scope is defined |
| `CHANGELOG.md` | Users and operators | Durable history of what actually shipped | A planning document |
| `docs/internal/release-cadence.md` | Maintainers with publish rights | Operational release runbook | A product roadmap |

## ROADMAP.md Standard

`ROADMAP.md` is the strategic map. It preserves the product direction and
release-line horizon, while linking to internal release roadmaps for detailed
release contracts.

Required sections:

1. **Header**
   - Current published build.
   - Active release horizon.
   - Last updated date.
   - Policy references.

2. **Version-Line Model**
   - One table row per version line.
   - Each row states the goal and the gate that opens the next line.
   - Future beta, RC, and GA lines must be labeled as future gates unless an
     active milestone has explicitly opened.

3. **Current Strategic Horizon**
   - The active release line and why it matters.
   - Strategic workstreams in priority order.
   - Links to active internal release roadmap docs.

4. **Future Horizon**
   - Future version lines and major workstreams.
   - Detail enough to preserve intent; link to internal future-horizon docs for
     step-by-step plans.
   - No checkbox-only rows such as "implement X" without a linked release or
     horizon doc that decomposes the work.

5. **Policy / Architecture Alignment**
   - References to controlling ADRs and canonical policy docs.
   - The roadmap may summarize ADR consequences; it must not duplicate or amend
     ADR text.

6. **Follow Along**
   - Links to changelog, ADR index, active milestone, public project board, and
     internal release roadmap index.

7. **Stability Commitments**
   - Short summary of stability by version line.
   - Link to controlling ADRs and compatibility commitment docs.

Roadmap rules:

- Keep strategic detail in `ROADMAP.md`; move release-specific checklists to
  `docs/internal/releases/`.
- Use "active", "planned", "future gate", or "closed" consistently.
- Do not mark beta, RC, or GA as active unless their release line has been
  explicitly opened.
- Do not delete a future workstream because it is not active. Move detailed
  steps into an internal release or horizon roadmap and link to it.
- Do not use `ROADMAP.md` as the source for what shipped. Once released, the
  shipped record lives in `CHANGELOG.md` and the historical internal release
  roadmap.

## Internal Release Roadmap Standard

Each release roadmap is a release contract. It records intent before release,
execution state during the release, and the historical disposition after tag.

Required filename:

```text
docs/internal/releases/<version>-roadmap.md
```

Examples:

```text
docs/internal/releases/v0.9.0a1-roadmap.md
docs/internal/releases/v0.9.0a2-roadmap.md
docs/internal/releases/v0.9.0a3-roadmap.md
```

Required sections:

1. **Header**
   - Release version.
   - Status: `historical`, `active`, `planned`, or `future gate`.
   - Release owner.
   - Milestone link, if active or historical.
   - Tag / release link, if historical.
   - Last updated date.

2. **Release Intent**
   - One or two paragraphs describing what this release is meant to accomplish.
   - State why this release exists in the version-line sequence.

3. **Scope Summary**
   - Table with `Area`, `In scope`, `Out of scope`, and `Canonical references`.
   - This is the quick answer to "what is this release?"

4. **Detailed Scope**
   - One subsection per workstream.
   - Each workstream must include:
     - objective;
     - included changes;
     - excluded/deferred changes;
     - evidence required;
     - issue or PR references.

5. **Artifact Surfaces**
   - PyPI packages.
   - npm packages.
   - GHCR images.
   - docs site / docs source.
   - Git tag / GitHub release.
   - Any intentionally non-shipped artifact.

6. **Security and Risk Posture**
   - Security posture summary for the release.
   - Advisory policy or GHSA references when relevant.
   - Threat-model or evidence-registry links.
   - Explicit residual risk and safe/unsafe deployment patterns.

7. **Evidence Gates**
   - Required validators, CI checks, release evidence, publish evidence, and
     manual verification steps.
   - Historical docs must record whether each gate passed, was deferred, or was
     intentionally out of scope.

8. **Release Notes Candidates**
   - User/operator-facing changes likely to become changelog or release-note
     entries.
   - At release close, reconcile this section against `CHANGELOG.md`.

9. **Deferred / Follow-Up Work**
   - Items intentionally moved out of the release.
   - Each item should name the next release horizon, issue, or future gate.

10. **Historical Disposition**
    - Required once the release ships.
    - State what shipped, what did not ship, tag date, and where the final
      release notes live.

Internal release roadmap rules:

- The document may be detailed, but it must not replace GitHub issues for live
  execution.
- Every "implement X" statement must be decomposed into concrete included
  changes or linked to a deeper planning doc.
- Historical release docs must not be rewritten to pretend deferred work
  shipped. Record the deferral and link the follow-up.
- Security-sensitive drafts stay in Internal-Comms until publication; once the
  fact is public and canonical, the long-term Stigmem release record lives here.

## Template

Use this skeleton for new release roadmaps:

```markdown
# <version> Release Roadmap

**Status:** active | planned | historical | future gate
**Release owner:** <name or role>
**Milestone:** <link or "not opened">
**Tag / release:** <link or "not tagged">
**Last updated:** YYYY-MM-DD

## Release Intent

...

## Scope Summary

| Area | In scope | Out of scope | Canonical references |
| --- | --- | --- | --- |
| ... | ... | ... | ... |

## Detailed Scope

### <Workstream>

**Objective:** ...

**Included changes:**
- ...

**Excluded / deferred:**
- ...

**Evidence required:**
- ...

**References:**
- ...

## Artifact Surfaces

| Surface | Expected artifact | Status | Evidence |
| --- | --- | --- | --- |
| PyPI | ... | ... | ... |
| npm | ... | ... | ... |
| GHCR | ... | ... | ... |
| Docs | ... | ... | ... |
| GitHub release | ... | ... | ... |

## Security and Risk Posture

...

## Evidence Gates

| Gate | Required evidence | Status |
| --- | --- | --- |
| ... | ... | ... |

## Release Notes Candidates

- ...

## Deferred / Follow-Up Work

| Item | Disposition | Target |
| --- | --- | --- |
| ... | ... | ... |

## Historical Disposition

...
```
