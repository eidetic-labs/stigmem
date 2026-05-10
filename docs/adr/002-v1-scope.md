# ADR-002: v1 critical-path scope

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Supersedes:** Implicit "ship everything we can build" scope of the v1.0 release
**Related:** ADR-001 (versioning), `stigmem/plans/version-prioritization.md`, `stigmem/plans/strengthening-plan.md`

---

## Context

The withdrawn v1.0 release contained substantial surface area — approximately 55,000 lines of code, an §1–§25 spec, multiple SDKs, multiple deployment targets, and a curator dashboard. The work is genuine engineering. What it lacked was independent validation: no operator soak, several known security gaps (per the OpenClaw audit and threat-model R-15), and a breadth that made it difficult to harden the core within a reasonable timeframe. v0.9.0-preview is the focused subset that the project can credibly commit to as v1.0 after Phase B hardening and operator validation.

Federated knowledge fabric earns trust by being rigorously correct on a small surface. Every feature past the critical path is a liability over time — code to maintain, security to audit, behavior to reason about, operator deployments to support. The marginal cost of writing code is low; the marginal cost of *correctness* across existing surface is meaningful and grows with size. The right tradeoff for v1.0 is a smaller surface that we can defend, not a larger surface that we hope to validate later.

This ADR defines the v1.0 critical-path scope: the smallest set of features and surfaces that earns the right to be called federated agent memory. Everything else moves to `experimental/` until it can return through the gates defined in ADR-008.

## Decision

The v1.0 critical-path scope is the following list. Anything not on this list is, by definition, not in v1.0.

### Protocol & data model

- Typed facts: `(entity, relation, value)` triple with provenance, confidence, scope, HLC timestamp.
- Scopes: `local`, `team`, `company`, `public`, with strict server-side enforcement.
- Operations: `assert_fact`, `query_facts`, `recall`. Everything else is built from these.
- Provenance: every fact carries source, timestamp, confidence at write; immutable in v1.

### Federation

- Two-node mTLS replication with TLS 1.3 floor.
- Ed25519-signed manifests at `/.well-known/stigmem-manifest.json`.
- Rekor inclusion proofs for manifest rotation events.
- Capability tokens: short-lived (≤90d), Ed25519-signed, verb+object validated at admission.
- Bounded HLC skew with per-peer drift tracking (R-19).
- Quarantine garden for federation inbound writes.

### Authentication and authorization

- Argon2id-hashed API keys (per ADR-007 migration).
- Enforced API key max-age (default 90 days).
- Per-principal token-bucket rate limits.
- Capability-based instruction handling (`interpret_as`) per ADR-003.
- Per-session read/write graph isolation (R-21 mitigation).

### Observability

- WAL-ordered audit log with 13 event types per §22.3, 90-day retention.
- Prometheus metrics for node health, request rates, quota state, federation peer status.

### Storage

- SQLite backend.
- SQLCipher at-rest encryption (opt-in, documented in OPERATING.md).

### Embedding

- Local `nomic-embed-text-v1.5` (default, offline).

### Adapters

- OpenClaw adapter v0.9 (hardened, with handoff allowlist; experimental flag until external operator soak).
- MCP adapter (minimal `assert_fact`, `query_facts`, `recall`, `lint_scope`).

### Operations

- Docker Compose reference deployment (`make demo`, `make demo-attack`).
- Container hardening: distroless base, non-root UID, read-only filesystem, seccomp.

### SDK

- Python SDK (`stigmem-py`).

### Documentation

- README, LIMITATIONS.md, SECURITY.md, OPERATING.md, THREATS.md, CHANGELOG.md, ROADMAP.md.
- Threat model and scenarios on docs front page.
- ADR-001 through ADR-008.
- Friday public engineering log.

### Release engineering

- Sigstore-signed releases (Phase C, required before v1.0.0 GA per R-22).
- Reproducible builds and SBOM publication (Phase C).
- Version-consistency CI check (per ADR-001).

### What is NOT in v1.0

Everything else. The complete deferred list is maintained in `stigmem/plans/version-prioritization.md`. Notably:

- §21 lazy instruction discovery, §23 RTBF tombstones, §24 time-travel queries, §25 CIDs, §17 memory garden, §18 source attestation, subscriptions.
- OIDC integration, multi-tenant isolation, fuzzy resolver.
- PostgreSQL backend, libSQL/Turso backend.
- Cloud embedding.
- Obsidian, Letta, Zep, Cognee, Gemini, OpenAI-tools, Paperclip adapters.
- Curator dashboard.
- Helm, Fly, systemd deployments; Grafana dashboards.
- Go SDK, TypeScript SDK.
- Billing hooks.

These items remain in the codebase under `experimental/` and will return individually under ADR-008's re-introduction gates.

## Alternatives considered

**1. Keep everything; harden incrementally.** Rejected. Harden-everything-incrementally was attempted in the lead-up to v1.0 and produced more surface than could be independently validated. Without a scope cut, the same pattern recurs: every PR touches a different feature, attention diffuses across surfaces, and the core never reaches "operator-defensible." The cut isn't optional; it's the precondition for hardening to converge.

**2. Cut more aggressively (drop MCP adapter, drop SQLCipher).** Rejected. MCP is the *integration* contract for the category — without it, stigmem is an isolated database. SQLCipher is opt-in and adds no maintenance burden when off.

**3. Cut less aggressively (keep §21 lazy instruction discovery; just label it experimental in v1.0).** Rejected. §21 is the prompt-injection surface (R-15, R-21). Until ADR-003 lands and is operator-validated, instruction-typed facts that flow into agent context are a category-defining risk. Shipping §21 in v1.0 — even with a warning label — invites exactly the deployments that will hit the worst-case failure modes.

**4. Defer the cut decision until after a beta period.** Rejected. The question "what's in v1?" is upstream of every other planning question (what to test, what to document, what to harden, what to threat-model). Deferring it leaves the strengthening plan and the security docs uncalibrated.

## Consequences

### What gets easier

- **Strengthening plan converges.** The strengthening plan now has a finite surface to harden. Every week's deliverables map to specific items on this list.
- **Threat model and scenarios calibrate cleanly.** Per the security-revisions document, the threat model can drop §21/§23/§24/§25 risks (R-15–R-18) into an `experimental-risks.md` companion, leaving the v1.0 risk register with a coherent set of risks all tied to the critical-path surface.
- **Adopter confusion drops.** "Is X supported?" has a yes/no answer for every X. Things on this list are supported (within the v0.9-preview caveats); things not on this list are explicitly experimental.
- **Operator surface is small enough to test.** External operator soak (Phase B) becomes feasible because the surface they're testing fits in their head.
- **CI becomes meaningful.** Conformance vectors and adversarial vectors target a defined surface; coverage metrics mean something.

### What gets harder

- **Some users of v1.0 lose features.** Anyone who integrated against §23 tombstones or the libSQL backend in v1.0 must either pin to that release (now yanked from PyPI) or migrate to v0.9.0-preview. The migration post sets expectations; this ADR formalizes them.
- **Saying no to features.** Internal pressure ("we already wrote it; why not include it?") and external pressure ("when does X land?") become recurring conversations. ADR-008 provides the structured answer.
- **`experimental/` directory becomes its own maintenance burden.** Code that compiles but isn't on the critical path still needs not to bitrot. Mitigation: experimental features have a build-but-don't-test policy until they enter the re-introduction process; broken experimental code is simply marked broken in the README until someone wants to revive it.

### New risks

- **R-SCOPE-1: scope creep via "small additions."** Each individual proposal to extend scope sounds reasonable in isolation. The sum of reasonable individual additions reproduces the v1.0 surface area. Mitigation: any change to this list requires an ADR-002 amendment with sign-off (two contributors or the founder alone, per ADR-001 §Contributor approval rule). No bypass during the strengthening plan.
- **R-SCOPE-2: experimental features rotting.** Code that nobody touches develops bugs that emerge years later. Mitigation: experimental features stay buildable but are not part of the test matrix. Re-introduction (ADR-008) requires bringing them up to v1.x quality, including tests.

### Cross-references to security docs

The threat model and scenarios should reflect this scope. Per the security-revisions punch list (P0-1), risks R-15 through R-18 (associated with §21–§25 features) move to an `experimental-risks.md` companion document. Risks R-19 through R-22 (HLC, embedding, worm vector, supply chain) stay on the v1.0 register.

The OpenClaw audit's findings (C1, C4, H1, H2, H4, etc.) are all in v1.0 scope — the OpenClaw v0.9 adapter is a v1.0 deliverable.

## Amendment process

This ADR is the contract that defines v1.0. Changes to the list require:

1. A new ADR (ADR-NNN) titled "Amendment to ADR-002: [feature name]".
2. Two contributors' sign-off on the amendment.
3. A corresponding update to `stigmem/plans/version-prioritization.md`.
4. A corresponding update to the strengthening plan if the amendment affects timeline.

The amendment process is deliberately costly. It is a feature, not a bug.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*