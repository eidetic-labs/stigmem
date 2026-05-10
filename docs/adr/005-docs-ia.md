# ADR-005: Documentation information architecture

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** ADR-002 (v1 scope), ADR-012 (version-aware feature exposure), ADR-013 (deprecation policy), ADR-014 (compatibility matrix); `stigmem/plans/master-checklist.md` §4.3a; `stigmem/analyses/docs-structure-review-2026-05-06.md`

---

## Context

The retracted v1.0 / v2.0 docs site organized content under five top-level tabs (Learn / Build / Operate / Reference / Community) with security buried as a sub-category under both Build and Operate. The threat model — the project's strongest engineering artifact — sat under Reference → Specification, two clicks deep.

This structure communicated: *security is a thing to remember*. The right structure for a federated agent-memory product communicates: *security is one of the four ways you engage with this product*.

Two further problems compounded the IA issue. First, content duplication: many topics had parallel pages in `concepts/`, `security/`, and `spec/` directories with no canonical owner — three voices on Memory Garden, four on Recall, five on Federation. Second, post-retraction calibration: Docusaurus config defaulted to `v1.1`, current was labeled `v2.0-draft`, and release-notes covered only the retracted version. The site lied about project state.

The reversion direction (master-checklist §4) declares **v0.9.0-preview as the first build.** Prior version *markers* (v0.2 through v2.0) labeled development checkpoints, not tagged releases. The spec *content* under those markers is real product specification — it is reviewed and migrated forward into v0.9.0-preview, not archived. The IA migration is therefore both a structural restructure and a calibration to the actual canonical version, in parallel with the section-by-section spec review.

## Decision

The docs site at `docs.stigmem.dev` is organized into four top-level tabs.

| Tab | Question it answers | Audience values |
|---|---|---|
| **Learn** | "What is stigmem and why would I use it?" | Evaluator, Integrator |
| **Build** | "How do I integrate with stigmem from my code?" | Integrator |
| **Operate** | "How do I run a stigmem node in production?" | Operator |
| **Secure** | "Can I trust this with my data and my federation peers?" | Security, Spec |

Each tab is self-contained — a reader can stay within one tab without crossing to another for routine tasks.

### Tab content distribution

**Learn:** Overview, Key concepts, Quickstart, Use cases, Roadmap.

**Build:** API reference (auto-generated from OpenAPI), SDK guides (Python, TypeScript, Go), Connector guides (MCP host adapters, runtime adapters, agent platforms, vault/note-taking), Integration patterns, Tutorials, How-it-works data-flow pages.

**Operate:** Deployment guides, Configuration reference, Runbooks (per ADR-004), Storage backends, Observability, CLI reference, Compatibility matrix (per ADR-014).

**Secure:** Overview, Threat model with risk register at the top, Scenarios (operator-facing narratives), Specification (the protocol contract — moved here from Reference because spec *is* the security artifact), Security architecture, Hardening guide, Disclosure policy, Advisories, Compatibility commitment (per ADR-013), Deprecated features (per ADR-013).

### What dissolves

- **Reference tab** dissolves. Content distributes:
  - API Reference → Build.
  - Specification → Secure.
  - Experimental Features page → replaced by an auto-generated index of pages with `stability: experimental` (per ADR-012).
  - Release Notes → top-level surface, linked from `/versions` hub; not a sidebar item.
  - Architecture pages → split: deployment topology to Operate; data-flow to Build.
  - Glossary → top-nav or footer utility.
- **Community sidebar** dissolves. Content distributes:
  - `security-disclosure.md` → Secure.
  - `project-resources.md` → top-nav or footer.
- **Blog** stays as a top-nav item alongside Docs / GitHub / Discord. Standard Docusaurus pattern.

### Frontmatter `audience` taxonomy

The `validate-audience` plugin extends from three to five accepted values:

| Value | Meaning |
|---|---|
| `Evaluator` | First-time visitor assessing whether stigmem fits their problem. Learn-tab content. |
| `Integrator` | Developer writing code against stigmem. Build-tab content. |
| `Operator` | Running a node in production. Operate-tab content. |
| `Security` | Security engineer or compliance team auditing the design. Secure-tab content. |
| `Spec` | Protocol contributor or spec implementer. Secure-tab content. |

Backfill on every page is part of the docs-restructure PR (master-checklist §4.3a).

### Cross-cutting principles

1. **Lead Secure with the risk register.** The most useful artifact for a security-minded evaluator is the current Mitigated/Residual/Open/Accepted status by version. That table goes at the top of the Threat Model page.
2. **Empty stubs are honest signaling.** Pages like "Bug bounty" or "Compliance notes" can ship as stubs marked "coming in vX.Y" rather than be hidden until ready. An empty stub at a stable URL is more honest than a missing page.
3. **Every page in `Operate` and `Secure` lists the version it applies to** via the `since` and `applies_to_version` frontmatter (per ADR-012).
4. **Security and operations cross-reference, but each is complete from its own audience's perspective.** An operator should be able to deploy stigmem from `Operate` alone; a security engineer should be able to evaluate it from `Secure` alone.
5. **One canonical page per topic.** Content deduplication pass (master-checklist §4.3a) resolves the existing 2-, 3-, and 4-way duplicates with `client-redirects` from retired URLs.

## Alternatives considered

**1. Keep five tabs (Learn / Build / Operate / Secure / Reference).** Rejected. Reference becomes a kitchen sink that re-creates the retracted v2.0 problem — content lives there because it doesn't fit anywhere else, accumulating until the IA collapses. Distributing Reference content forces every page to have a clear primary home.

**2. Three tabs (Learn / Build / Operate) with security under Operate.** Rejected. This is the conventional structure and it's what the retracted docs effectively did. For a category where trust *is* the product, demoting security to a sub-section sends the wrong signal.

**3. Audience-named tabs ("For Operators," "For Security Engineers").** Rejected. Verb-named tabs (Learn, Build, Operate, Secure) parallel each other grammatically and signal action. Audience-named tabs imply rigid role boundaries; a developer might genuinely need to read both Build and Secure for the same feature. The audience field captures audience metadata at the page level instead.

**4. Spec under Build.** Considered. Spec is normative and developers do read it. Rejected because security engineers also read it (often more carefully), and the Build tab's primary audience is integration developers building applications, not protocol implementers. Putting spec under Secure makes the protocol's normative status — what we commit to — peer to threat-model and security architecture, which is the right framing.

**5. Versioned sidebar per tab from day one.** Accepted (was rejected in earlier draft). With `v0.9.0-preview` as the first build and the policy "snapshot every release," activating Docusaurus versioning from the start is correct. Discipline starts on day one is cheaper than retrofitting at v1.0 stable.

## Consequences

### What gets easier

- **Reader navigation matches reading intent.** Each audience finds their content in one tab.
- **Security content has room to grow.** Threat-model versions, scenario docs, advisories, hardening guides, runbooks, post-mortems all have a natural home.
- **Recruiting beacon.** Security-minded engineers — exactly the people we want as contributors — navigate to Secure first when they find the docs.
- **Documentation discipline.** Every new feature has to answer "what does this add to each tab?" before it ships.
- **Spec is no longer hidden.** Promoting Specification to Secure surfaces the protocol's normative content where evaluators look first.

### What gets harder

- **Cross-references multiply.** "Hardening" appears in both Operate and Secure with different framings; the two pages must stay synchronized. Mitigation: one canonical page per topic, cross-linked from the other tab rather than duplicated.
- **IA migration is expensive.** ~1 day of structural moves, ~1 day of redirect setup, ~1 day of cross-link sweeps. Lands in master-checklist §4.3a (PR 2.5).
- **Stub maintenance.** A stub that says "coming in v1.0" but still says so two years later is a credibility leak. Mitigation: dated placeholder headers; remove or backfill on each release.

### New risks

- **R-IA-1: tab content drifts in scope.** The Operate tab might accumulate security content that should live in Secure (or vice versa). Mitigation: tab-ownership labels in the docs source via `audience` frontmatter; PR review checks tab fit when new pages are added; `validate-audience` plugin enforces vocabulary.
- **R-IA-2: nav crowding.** Each tab can hold roughly 10–15 visible items in the sidebar before navigation collapses. Mitigation: nest sub-pages under topics once a tab approaches that bound; do not add new top-level tabs to relieve pressure.
- **R-IA-3: external links to retired URLs.** Anyone who linked to `/v0.2/`, `/v1.1/`, `/reference/`, or `/community/` URLs gets a 404 unless redirected. Mitigation: `client-redirects` plugin already installed; redirect every retired URL to the closest canonical equivalent.

## Implementation plan

This ADR ships in Phase A of the strengthening plan, owned by the team. Operationalized in master-checklist §4.3a (PR 2.5 — Docs site restructure and reversion sweep).

- Restructure `docs/sidebars.js` for the four-tab navigation.
- Move all `security/` pages into the unified Secure tab.
- Move spec pages into Secure under "Specification."
- Distribute Reference content per the table above.
- Distribute Community content per the table above.
- Extend `validate-audience` plugin to the five-value taxonomy; backfill `audience` on every page.
- Set up `client-redirects` for every retired URL.
- Activate `versioned_docs/` with `v0.9.0-preview` as the canonical default (per ADR-001 versioning + ADR-012 version-aware exposure).

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*