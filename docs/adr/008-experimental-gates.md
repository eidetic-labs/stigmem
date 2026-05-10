# ADR-008: Re-introduction gates for v2.0.0-experimental features

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** ADR-001 (versioning), ADR-002 (v1 scope), `stigmem/plans/version-prioritization.md`

---

## Context

ADR-002 cuts the v1.0 critical-path scope to a defensible minimum and moves the rest of the codebase to `experimental/`. The cut features are not deleted — they are in the codebase, importable with explicit opt-in, ready to return.

The question this ADR answers: **what does it take for an experimental feature to come back?**

Without a structured re-introduction process, the project is one well-meaning PR away from re-creating the retracted v1.0 — surface area accumulating faster than correctness can keep up. With a structured process, every feature's return is a deliberate decision with measurable gates, and the v1.0 critical-path stability is preserved.

The process needs to be costly enough that scope-creep is real friction, but not so costly that legitimately-ready features get permanently stuck. The five gates below are calibrated to that balance: each gate produces a concrete artifact, none requires more than ~1 week of focused work, and all five together represent the cost of bringing a feature to v1.x quality.

## Decision

A feature in `experimental/` returns to a default-on, supported state only after passing all five gates in order.

### Gate 1: Threat-model delta

The feature's author writes a delta document at `spec/security/deltas/<feature>-threat-model.md` that addresses:

- What new trust boundaries does this feature introduce, or what existing ones does it modify?
- What new STRIDE entries apply per affected boundary?
- What new risks (R-XX entries) does the feature introduce, with likelihood, impact, priority, and proposed mitigations?
- Which existing risks does the feature affect (e.g., does it widen R-05 prompt-injection surface)?

The delta is reviewed and accepted (two contributors or the founder alone, per ADR-001 §Contributor approval rule), then merged into the threat model. A feature without a threat-model delta does not pass Gate 1.

### Gate 2: ADR drafted and merged

A new ADR captures:

- The design decision (the feature's shape in v1.x).
- The migration story from the experimental version (which APIs change, which deprecations apply).
- Alternatives considered.
- Consequences, including new risks.

The ADR may explicitly supersede or amend earlier ADRs (most often ADR-002, the scope contract). An ADR-002 amendment follows the ADR-001 §Contributor approval rule: two contributors or the founder alone.

### Gate 3: Conformance vectors

The feature's wire-format and behavioral contract are encoded as conformance vectors at `data/conformance/<feature>/`, including:

- Positive cases (correct behavior).
- Negative cases (validation failures, error responses).
- **Adversarial cases** at `data/conformance/<feature>/adversarial/` — malformed inputs, injected payloads, edge cases the threat-model delta identified.

Vectors are wired into CI as a blocking job. PRs that break the conformance suite fail to merge.

### Gate 4: 30-day external operator soak

At least one external operator runs the feature in a real workload for 30 days, with public bug reporting in the stigmem GitHub issues. The operator does not have to be a paying customer; they can be a community contributor, a partner organization, or a paid soak partner — the only requirement is that they are not the original feature author.

The soak produces:

- A public LOG.md entry summarizing what was found, what was fixed, what remains open.
- At least one closed issue tagged `<feature>-soak-finding`. Soaks that produce zero findings are suspect — either nothing was tested or the soak wasn't real; either way, Gate 4 fails.

### Gate 5: Documentation parity

The feature has documentation across all four tabs (per ADR-005):

- **Learn:** if the feature affects the conceptual model, an explanation appears under Key Concepts.
- **Build:** API reference, SDK examples, integration patterns.
- **Operate:** configuration reference, hardening guidance, runbook updates if the feature affects observability.
- **Secure:** scenarios under `docs/security/scenarios.md` covering the feature's risks; threat-model delta linked.

If the feature doesn't need a presence in a given tab (e.g., a backend driver doesn't need Learn coverage), that's documented in the ADR (Gate 2).

### Order matters

The gates are sequential. Gate 1 (threat model) before Gate 2 (ADR), because the design decision should be informed by the security analysis. Gate 3 (conformance) before Gate 4 (soak), because the operator should soak against a behaviorally-defined contract, not a moving target. Gate 5 (docs) at the end, because docs against a still-changing implementation rot before they ship.

### What about features that legitimately don't need all five gates?

Some experimental features may not warrant the full process — for example, a build-tooling improvement that's experimental only because it wasn't tested on enough operating systems. In those cases:

- The author proposes a reduced-gate path in their ADR (Gate 2).
- Two contributors sign off explicitly on which gates are skipped and why.
- The reduced-gate path is documented in the ADR for institutional memory.

The default is all five gates. Skipping is exception, not rule.

## Alternatives considered

**1. No gates; let maintainer judgment decide.** Rejected. Maintainer judgment is exactly what produced the retracted v1.0. The gates exist precisely to provide structure that survives the temptation to "just include this one feature."

**2. Fewer gates (drop the 30-day soak; rely on internal testing).** Rejected. The 30-day external operator soak is the single highest-value gate. Internal testing finds the bugs the authors anticipated; external soak finds the bugs the authors didn't think to test for. Skipping it is the part that matters.

**3. More gates (add a security review by an external auditor).** Considered for v1.0.0 GA but not for individual feature re-introduction. External auditing is a fit for major version releases; individual features get covered by the threat-model delta plus conformance suite plus soak.

**4. Time-based gates ("a feature can re-enter after 6 months in experimental").** Rejected. Time alone proves nothing; a feature that sat untouched for 6 months is no closer to ready. The gates are about evidence of readiness, not duration of waiting.

**5. Combine all gates into a single "feature readiness review."** Rejected. Five distinct gates each produce a distinct artifact. A combined review tends to compress into a single conversation that ends in "looks good" — which is what we're trying to avoid.

## Consequences

### What gets easier

- **Adopter clarity.** "Is feature X supported?" has a clean answer: either it has passed all five gates (supported) or it hasn't (experimental). No middle ground, no "supported with caveats."
- **Maintainer focus.** Re-introduction work is a known process with known artifacts. Authors of experimental features have a roadmap to making their feature first-class.
- **Trust accumulation.** Each feature that passes the gates demonstrates the project's discipline. Over time, the gate process itself becomes a credibility signal — "stigmem's promotion bar is high" is exactly the reputation we want.
- **Resistance to scope-creep.** When someone proposes "let's just turn on §23 tombstones, they're already written," the answer is "great, here are the five artifacts you need to produce." Most proposals don't survive Gate 1.

### What gets harder

- **Per-feature re-introduction is real work.** Authors who shipped quickly into experimental will find the path to v1.x slower than the path to experimental was. This is a feature.
- **Some features may never pass.** If a feature can't produce a credible threat-model delta, or no operator wants to soak it, that's information — the feature probably shouldn't ship at v1.x quality. We accept that some experimental features will live in `experimental/` indefinitely.
- **Process overhead in PR reviews.** Every feature-promotion PR triggers gate-checking. Mitigation: gate status is tracked in a dedicated `experimental/<feature>/STATUS.md` file; PR templates ask "does this PR change gate status?"

### New risks

- **R-GATE-1: gate gaming.** An author who wants to ship faster might produce a perfunctory threat-model delta or a soak with one cooperative operator. Mitigation: contributors' sign-off on each gate; community can call out perfunctory artifacts publicly.
- **R-GATE-2: features stuck behind one gate.** A feature with a clear threat model and ADR but no available soak operator can't progress. Mitigation: the contributors can act as soak operators in extreme cases (with the soak duration extended to 60 days to compensate for the contributor's existing familiarity).
- **R-GATE-3: gate inflation.** Future ADRs might add more gates, making the process unsustainable. Mitigation: this ADR fixes the gates at five; adding gates requires an ADR-008 amendment with contributors' sign-off.

## Implementation plan

This ADR takes effect immediately on acceptance. No code changes are required for v0.9.x — the gates apply to features attempting re-introduction, of which there are none until at least v1.0.0 GA.

After v1.0.0 GA, the first feature to attempt re-introduction will road-test the process. Lessons learned from that road-test feed an ADR-008 amendment if needed.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*