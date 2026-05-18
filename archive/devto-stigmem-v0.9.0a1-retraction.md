<!--
This file is the **canonical source** of the v0.9.0a1 retraction post:
the public dev.to announcement of the reset. The stigmem repo is its
authoritative home; the dev.to publication mirrors this content.

Lives under archive/ because (a) it sits outside the Docusaurus blog
tree (docs/blog/) so the build pipeline doesn't process it as a current
blog post, and (b) once the dev.to publication goes live, this file
also serves as the in-repo historical record of what was published.

Once published, fill in the dev.to URL in the canonical_url frontmatter
field below.

Editing policy: this file is the pre-publication source of truth; edit
freely until publish. After dev.to publication, do not modify in place.
If the published post needs a correction, ship a follow-up post or
PEP 440 .post1 errata per docs/internal/release-cadence.md §Rule 3,
and add a new archive entry rather than modifying this one.
-->

---
title: "Walking Back Our v1.0 Announcement: Resetting to v0.9.0a1 as the First Build"
published: false
description: Last week we announced v1.0 of stigmem. That label was wrong, and on review the broader version history was overstating maturity too. Here's what we got wrong, what we're changing, and what we'd recommend for anyone evaluating stigmem today.
tags: opensource, ai, agents, security
canonical_url: https://dev.to/offbyonce/walking-back-our-v10-announcement-resetting-to-v090a1-as-the-first-build-al0
---

Last week we announced v1.0 of [stigmem](https://github.com/eidetic-labs/stigmem), our federated agent memory project.

That label was wrong. We're walking it back. And on review, the broader version history we'd been carrying (v0.2 through v2.0 across our spec files and versioned docs) was overstating the project's maturity in the same way. None of those were tagged releases anyone deployed in production; they were development checkpoints. The version *labels* on them implied a release chronology we hadn't earned. (The spec *content* is real and current; we're reviewing it section by section as part of this reset, not throwing it away.)

So we're doing two things together: walking back the v1.0 announcement, and resetting the canonical version line. **v0.9.0a1, a preview alpha, is the first build of stigmem.** The spec is being reviewed and improved into the v0.9.0a1 canonical structure: core sections first, then experimental ones move to clearly-labeled experimental status. Nothing from the spec is being deleted.

This post explains what happened, what we're changing, and what we'd recommend for anyone evaluating stigmem today. If you came in on the v1.0 announcement and have already integrated against it: please read the "If you were planning to deploy this week" section below before continuing.

## Why the v1.0 label was premature

The most direct evidence is in our own threat model. We publish one: it's a real STRIDE analysis with a per-trust-boundary risk register, and you can read it [here](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md). Reading it carefully, several controls that should be table stakes for "v1.0 stable" are still open:

- mTLS for federation (not enforced by default)
- Per-principal rate limits
- Enforced API key max-age and rotation
- A persistent audit log with operator-actionable event types
- Capability-level validation for cross-org instruction handling
- Bounded-skew enforcement on hybrid logical clocks across federated peers

The controls our own document says are required to ship safely are not yet in place. v1.0 should mean those are done. They aren't.

Our previous risk register attributed these mitigations to an internal hardening milestone that hadn't shipped when the v1.0 announcement went out. The label outpaced the work. (We've since updated the register to a v0.9.0a1 baseline that names what's actually in effect today versus what's still in flight.)

## What happened

The shipping pace outran our validation cycle.

Stigmem is built by two people with heavy AI-coding assistance. That setup makes it remarkably fast to ship code, fill out spec sections, generate test scaffolding, polish documentation. It does not make it fast to *validate* that what you've built behaves correctly under adversarial conditions, especially in a federated system where the threat model includes peers who lie.

Velocity ran ahead of validation. We had a spec through §25, a versioned docs site, multiple SDKs, conformance vectors, and a deployment story, all of it shipped in days. None of that proves the federation primitives are correct under adversarial conditions. That requires external operators, and we had zero.

## What's changing today

Concrete actions, all landing this week:

1. **Re-versioned to v0.9.0a1 as the first build.** The `pyproject.toml`, README, docs, and GitHub release reflect this. v0.9.0a1 is the first public release of `stigmem`, `stigmem-py`, `stigmem-node`, and `stigmem-openclaw` on PyPI, and of `@eidetic-labs/stigmem-ts` on npm. (See *What the audit found* below for the precise pre-publish state on PyPI and npm.)

2. **The threat model moves to the docs front page**, not buried under `spec/security/`. It now includes a per-release status header naming which risks are mitigated, residual, open, and accepted as of the current version. This will be updated on every release; the changelog reflects it.

3. **A milestone-based plan to v1.0.0 is published openly.** It includes a capability-based redesign of our prompt-injection handling (replacing the sanitizer-stripping approach we currently use, which doesn't survive contact with motivated adversaries), federation hardening (mTLS by default, bounded HLC skew, per-peer drift tracking), persistent audit log, and, critically, a 30-day public soak with at least one external operator before v1.0.0 ships. The plan is in [`ROADMAP.md`](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md), with regular engineering log posts to come.

4. **We've cut surface.** A substantial set of features that were labeled v1.0 are moving to `experimental/` as opt-in, gated work: RTBF tombstones, time-travel queries, lazy instruction discovery, advanced memory-garden ACL, source attestation, multi-tenant isolation, the curator dashboard, OIDC SSO, billing hooks, multi-backend storage, several connector adapters (Letta, Zep, Cognee, Gemini, OpenAI-tools, Paperclip), Helm/Fly.io/systemd/PaaS deploy recipes, and additional SDK languages. Each re-emerges through structured reintroduction gates (threat-model delta, ADR, conformance vectors, 30-day operator soak, documentation parity), with no default-on path until those gates pass. Content-addressed fact IDs (CIDs) stay in core: they're load-bearing for our storage-immutability stack and prompt-injection trust boundary, so they're a default-install feature in v0.9.0a1, not deferred. Our v1.0.0 surface will be smaller than what we announced, and defensible.

5. **We're disclosing AI-authorship clearly.** The README and `CONTRIBUTING.md` now name which paths in the codebase have been human-reviewed in depth and which haven't. This shouldn't be a controversial disclosure, but in a category where trust is the product, hiding it would have been worse than naming it.

### What the audit found

When we audited what we'd actually shipped under the v1.0 label, we found that most of the artifacts that would have made it real never landed. Neither `stigmem` on PyPI nor any `stigmem*` package on npm was ever published; the canonical-package names were still unclaimed at the time of the audit. The OpenClaw adapter (`stigmem-openclaw`) did upload to PyPI at v1.0.3 and v1.0.5, but both declared `stigmem-py>=1.0.0rc1` as a hard dependency, and `stigmem-py 1.0.0rc1` was never published either. Those adapter uploads were end-to-end uninstallable: the listing existed, the wheel was downloadable, but `pip install stigmem-openclaw` failed with an unsatisfiable constraint.

We're correcting that as part of this reset. v1.0.3 and v1.0.5 are yanked from PyPI (PEP 592: they remain reachable for anyone who pinned them, but new resolutions skip them). `stigmem-openclaw 0.9.0a1` ships alongside the canonical packages and is the first installable version of the adapter. The ClawHub package (`clawhub.ai/offbyonce/stigmem-node`) is updated with the package README pointing at this retraction post.

The spec content from earlier development checkpoints is being reviewed section by section against actual implementation and migrated into the v0.9.0a1 canonical spec. The original evolutionary snapshots move to `spec/archive/evolution/` as reference material once their content has been forward-migrated. Nothing about the spec is being deleted.

## What's not changing

The core idea (a federated, typed, provenance-tracked memory substrate for AI agents) is still right. The design instincts that produced manifests with Rekor inclusion, Ed25519-signed capability tokens, scope/garden ACLs, and a real STRIDE threat model are still right.

What changes is the pace at which we earn the right to call any of this "stable."

## If you were planning to deploy this week

Wait until the hardened-core milestone (`v0.9.0bN` beta series) ships.

Specifically: do not run stigmem federation across organizational boundaries until the hardened-core milestone ships. The federation primitives (peer authentication, capability scoping, replication, instruction handling) are exactly the surfaces that need the open mitigations to be safe.

For single-org, single-node deployments where you're experimenting and have no production data dependency, v0.9.0a1 is reasonable to play with. The new [`LIMITATIONS.md`](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md) in the repo is honest about which of the open risks affect which deployment patterns; read it before you build against the API.

We aren't committing to a calendar for the hardened-core milestone; we'll complete it at a pace that aligns with our resourcing, and we'll publish updates as each item lands. Subscribe to the repo or watch the engineering log for progress.

If you've already integrated against v1.0: nothing about your code needs to change today. The core wire format hasn't changed. Some endpoints from v1.0 (RTBF tombstones, time-travel queries, lazy instruction discovery) moved to experimental and are not in the default install of v0.9.0a1, so applications relying on those will need to install the corresponding `experimental/<feature>/` plugin (when it ships) or pin to a v1.0 era image. v0.9.0a1 comes with no stability guarantee; expect breaking changes during the `v0.9.0aN` alpha and `v0.9.0bN` beta series. We'll document them in the changelog.

## We're looking for our first external operator

If you're an AI-tooling team, agent-framework project, or dev-tools company with agent workflows already in production: we'd like to talk. We're looking for one operator willing to run a stigmem node for 30 days against a real (non-critical) workload, with public bug reporting. We'll help you set up, watch you hit the bugs we couldn't anticipate, and credit you prominently in the v1.0 release notes when we get there.

This is the single most valuable contribution to the project right now. More than any feature, more than any spec section. If you're interested, [open an issue](https://github.com/eidetic-labs/stigmem/issues) tagged `operator-candidate` or reach out directly.

## The asymmetric thing about this category

Federated memory infrastructure earns trust by being boring and correct, not exciting and broad. The teams that try to be exciting and broad mostly disappear. The teams that get boring and correct mostly compound.

We chose exciting and broad first. We're correcting it now.

If you saw the v1.0 announcement, evaluated stigmem, and walked away because something didn't smell right. Your instincts were good. v1.0.0 will be worth re-evaluating once the hardened-core milestone ships.

---

The full roadmap, threat model, limitations doc, and OpenClaw adapter audit are all in the repo. Honest feedback, harsh issues, and contributor PRs all welcome, especially from anyone who's been burned before by infrastructure that overpromised at v1.0.

Eidetic Labs
[github.com/eidetic-labs/stigmem](https://github.com/eidetic-labs/stigmem) · [stigmem.dev](https://www.stigmem.dev) · [docs.stigmem.dev](https://docs.stigmem.dev)
