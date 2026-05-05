---
id: roadmap
title: Roadmap
sidebar_label: Roadmap
description: The Stigmem v2 roadmap — phase summaries, target quarters, and what each phase delivers for operators and integrators.
---

# Roadmap

*Last updated: Q3 2026. Audience: operators, integrators, spec contributors.*

---

Phases 0–7 are complete. The full history — what shipped, key architectural decisions, and lessons learned — is on the [State of Stigmem](./about/state-of-stigmem.md) page. This page covers what is coming next, in the order it ships, and what it means for you as an operator or integrator.

The v2 build plan runs seven phases (8–14), roughly 22 weeks, with meaningful parallelism between phases once the early trust and storage foundations are stable. Target timelines are given in calendar quarters; exact dates depend on community feedback and how earlier phases land.

**Current status:** Phases 8–13 are complete. Phase 13 shipped TypeScript and Go SDKs, the eval harness (79 adversarial scenarios + 400 recall probes), full observability (Prometheus + OpenTelemetry + Grafana), RTBF tombstones (§23), time-travel queries (§24), and content-addressed fact IDs (§25). The [SDK Quickstart tutorial](/docs/tutorials/sdk-quickstart) covers all three language ecosystems. **Phase 14 (Spec v2.0) is next.** All subsequent phases are sequenced but their scope can shift as earlier phases land.

---

## Phase 8 — Trust & Persistence Foundation ✓ Done

**Shipped: Q2 2026**

Phase 8 establishes the trust and storage foundations the rest of the plan depends on. It runs in two parallel streams:

**Documentation and community surfaces (Phase 8a — shipped):**
This page, the [Backends](./backends.md) guide (including the libSQL how-to, at-rest encryption section, and backup/restore runbook), the [Federation Trust guide](./guides/federation-trust.md), the [Security & Pen Testing](./contributing/security.md) contribution guide, and the [Project Resources](./community/project-resources.md) page are live. The [Two-Org Federated Network tutorial](./tutorials/two-org-federation.md) is the Phase 8 community-facing walkthrough that proves the trust story end-to-end.

**Federation trust architecture (§19 — shipped in spec v1.1):**
Spec §19 "Federation Trust" is normative in v1.1. The [Federation Trust guide](/docs/guides/federation-trust) covers operator setup end-to-end. Key capabilities:

- **Org manifests** — each operator publishes an org manifest (Ed25519 keypair, entity-URI list, rotation events) pinned in a transparency log (Rekor or Sigstore-equivalent). Rotation events are append-only and cryptographically linked.
- **Cross-org capability tokens** — writing scope `S` on a peer node requires a short-lived capability signed by the scope owner. Capabilities are revocable via the transparency log and carry explicit subject + verb + object.
- **Source-trust score** — every incoming fact receives a trust multiplier `t ∈ [0,1]` derived from identity strength, peer history, scope authority, and attestation mode. Effective confidence at recall time = `confidence × t`. Facts below a configurable threshold land in a **quarantine garden** for human review before entering the main fact store.
- **Provenance chain** — facts gain `derived_from: [fact_hash...]` and `attestation_chain: [signature...]` for tamper-evident audit.
- **Recall-time content sanitizer** — strips known prompt-injection sentinels from `value` fields when rendering into agent context. Documented as part of the recall contract.

**Persistent storage backends:**
A `StorageBackend` adapter trait replaces the single-SQLite assumption. libSQL (Turso-compatible) ships as the first non-default backend. SQLCipher at-rest encryption is available as an opt-in. Signed snapshot backup and restore with point-in-time recovery for libSQL. See the [Backends](./backends.md) page for the full matrix and decision guide.

**What this means for operators:** hosted deployments can switch from ephemeral SQLite to a persistent libSQL volume without changing application code. Federation between organizations becomes auditable and revocable. The quarantine garden gives admins a review surface for untrusted writes before they enter the canonical fact store.

---

## Phase 9 — Graph Memory & Recall ✓ Done

**Shipped: Q2 2026**

Phase 9 makes Stigmem useful as a memory substrate for agents that need to retrieve *relevant* facts rather than query by exact predicate. It ships the graph index, vector embeddings, and the `recall` endpoint that are the primary agent call surface going forward. Spec §20 "Recall & Graph" is **normative** in v1.1.

- **Graph adjacency index** — entity-to-entity relation traversal in O(edges), built as an incremental side index on the existing fact table. Exposed via `GET /v1/graph/neighbors` (§20.1).
- **Vector embeddings** — each fact embedded as a composed `"{entity} {relation} {value}"` string at write time. sqlite-vec for SQLite/libSQL. Default model: `nomic-embed-text-v1.5` (offline, Apache-2.0). Cloud opt-in via `STIGMEM_EMBED_MODEL_PROVIDER=openai`. (§20.2)
- **`recall` endpoint** — `GET/POST /v1/recall` with `query`, `token_budget`, `depth`, and `weights` parameters. Three-stage hybrid pipeline (lexical + dense + graph) fused with MMR packing. Entity-centric queries return the memory card first. (§20.3)
- **Memory cards** — per-entity synthesized summaries stored in the `memory_cards` table, materialised by a stale-on-write / refresh-on-read pattern. Every `assert_fact` call marks the entity's card stale; the next `recall` or `GET /v1/cards/{entity_uri}` call re-materialises it. Fresh, high-confidence (`avg_confidence ≥ 0.5`), contradiction-free cards short-circuit raw-fact re-ranking in the recall pipeline (fast-path). Cards with contradictions or stale confidence fall through to full raw-fact ranking (divergence policy). Python SDK: `MemoryCard` model + `client.get_card()`. (§20.4)
- **Subscriptions** — agents register push notifications (`on_change: webhook|wake`) on a scope or entity via `POST /v1/subscriptions`. Push instead of poll; garden ACL is re-evaluated on every event delivery. Security review of subscription auth (§20.5.5) and cross-garden recall scoping complete. (§20.5)
- **Causal links** — `derived_from: [fact_hash...]` on fact records enables audit chains; `GET /v1/facts/:id/provenance` walks the full derivation graph. (§20.6)
- **Python SDK** — `StigmemClient.recall()`, `StigmemClient.get_card()`, and async equivalents; `MemoryCard` model exported from `stigmem`.

**Documentation shipped with Phase 9:**
- [Recall guide](/docs/guides/recall) — when to use `recall` vs. `query_facts`, token-budget packing, weight tuning, memory card fast-path.
- [Memory Cards guide](/docs/guides/memory-cards) — card lifecycle (stale-on-write, refresh-on-read), divergence policy, `GET /v1/cards/{entity_uri}`, Python SDK.
- [Python SDK reference](/docs/guides/python-sdk) — `StigmemClient` / `AsyncStigmemClient` full API, `MemoryCard` model, exceptions.
- [Embeddings guide](/docs/guides/embeddings) — model selection, dimensionality, mixed-model safety.
- [Subscriptions guide](/docs/guides/subscriptions) — webhook and wake delivery, circuit breaker, replay window.
- [Tutorial: Agent with Recall](/docs/tutorials/agent-with-recall) — complete walkthrough building a token-efficient recall agent.
- [API Reference](/docs/api-reference) — recall, cards, graph, subscriptions, and provenance endpoints.

**What this means for operators:** agents calling Stigmem no longer pull full fact tables. `recall` fits relevant memory into a token budget automatically. Subscriptions eliminate polling loops for agents watching shared entities.

---

## Phase 10 — Lazy Instruction Discovery ✓ Done

**Shipped: Q2 2026**

Phase 10 applies the recall primitive to the agent-instruction problem. Today, agents load all instruction files (role specs, skills, memory files) at every conversation start even when most of the content isn't relevant to the current task. Phase 10 fixes this.

- **Boot stub** (~500 tokens) — identity, role, heartbeat-contract pointer, manifest pointer, and a `recall_instruction(topic)` tool. Replaces full instruction-file preloads.
- **Instruction manifest** (~1k tokens) — an indexed list of every instruction file/section with 1-line descriptions and load triggers (intents, keywords, task types). Always loaded; body content loaded on demand.
- **`recall_instruction` skill** — wraps the Stigmem `recall` endpoint against an `instruction:` scope. Agents call it when a heartbeat intent matches an instruction's triggers.
- **Stigmem-backed instructions** — existing instruction files are migrated to atomic facts under `instruction:agent:{role}` and `skill:{name}` scopes. The markdown files become generated artifacts from the canonical Stigmem store.
- **Discovery audit tool** — logs per heartbeat what the agent loaded vs. what it would have needed. Used to tune manifest descriptions and triggers before flipping the boot stub.
- **Caching** — the boot stub + manifest are cache-stable across turns; recall results are short and per-task.

**Documentation shipped with Phase 10:**
- [Lazy Instructions guide](/docs/guides/lazy-instructions) — boot stub format, manifest schema, chunk authoring, trigger design, and token-budget planning.
- [Instruction Migration guide](/docs/guides/instruction-migration) — `stigmem instruction migrate` CLI reference.
- [Tutorial: Authoring Lazy-Discovery Instructions](/docs/tutorials/authoring-lazy-discovery-instructions) — end-to-end walkthrough with real coverage and token numbers.

**What this means for operators:** agents running on Stigmem-backed instructions pay per-call context costs only for relevant content. Two production rollouts have completed the shadow audit and flipped to `migration_mode: lazy`:

- **Agent A — large instruction set** (3,190t eager baseline): stable 415t per heartbeat = 13.0% of baseline. 11/11 eval heartbeats at 100% coverage, 0 regressions.
- **Agent B — small instruction set** (1,129t eager baseline): 356–565t bimodal range = 31.5–50.0% of baseline. The bimodal profile reflects two intent classes (task-execution vs. architecture/design); both modes maintain 100% critical-chunk coverage. 11/11 eval heartbeats, 0 regressions.

The token budget calibration differs by instruction set size: large sets (> 3,000t) target ≤ 25% of eager baseline; small sets (≤ 1,500t) target ≤ 50%. Both represent meaningful savings — 87% reduction on Agent A's 3,190t set, 50% reduction on Agent B's 1,129t set.

---

## Phase 11 — Hosting Reference, Backend Matrix & Obsidian Adapter ✓ Done

**Shipped: Q3 2026**

Phase 11 completes the operator runbook and ships the Obsidian integration that makes Stigmem accessible to the memory-first / vibe-coder audience.

**Hosting recipes** (`deploy/` directory at repo root):
- **Fly.io** — `fly.toml` + persistent volume + libSQL embedded replica + healthchecks + scale-to-zero. The reference deployment for most hosted operators.
- **Docker Compose** — laptop/VM single-host deployment.
- **Helm** — Kubernetes / enterprise.
- **systemd** — bare metal / air-gapped.
- **PaaS one-pagers** — Render, Railway, AWS App Runner, GCP Cloud Run.

**Postgres backend** (feature-flagged) with pgvector support.

**Conformance test suite** published and runnable against all three production backends (SQLite, libSQL, Postgres). Independent adapter and node implementations can use it to verify compliance.

**Operator's handbook** ([Operator's Handbook](/docs/operating)) — backend selection decision tree, backup/restore runbook, peer setup, key rotation, monitoring, and cost calculator.

**Obsidian vault adapter** — two distribution forms:

1. **CLI/daemon** (`adapters/obsidian/`) — bidirectional sync between a Stigmem node and an Obsidian vault. Markdown notes become entities; frontmatter keys/values become typed facts; `[[wikilinks]]` become relations; inline `key:: value` (Dataview syntax) becomes facts. Renames tracked via link-update events. Conflicts surfaced as Obsidian markdown comments for in-vault resolution. See the [Obsidian Vault Adapter guide](/docs/guides/connectors/obsidian).
2. **Obsidian community plugin** (`adapters/obsidian-plugin/`) — same sync engine inside Obsidian's process, plus command-palette `Recall related memories`, a sidebar showing graph neighbors from Stigmem, and inline fact rendering. See the [Obsidian Plugin guide](/docs/guides/connectors/obsidian-plugin).

Logseq, Dendron, and plain-markdown vaults are supported via config — same adapter primitives, different vault-format flag.

**Documentation shipped with Phase 11:**
- [Operator's Handbook](/docs/operating) — eight pages covering backend selection, deploy runbooks, federation setup, backup/restore, key rotation, monitoring, and cost estimation.
- [Obsidian Vault Adapter guide](/docs/guides/connectors/obsidian) — CLI/daemon reference.
- [Obsidian Plugin guide](/docs/guides/connectors/obsidian-plugin) — in-process sync, recall sidebar, settings reference.
- [Tutorial: Self-host a stigmem node and sync your Obsidian vault](/docs/tutorials/self-host-obsidian) — end-to-end walkthrough from zero to working node + synced vault, including deploy-time and sync-throughput numbers.

**What this means for operators:** everything needed to run Stigmem in production on any platform is documented and tested. Obsidian users get a first-class bidirectional integration without leaving their vault. The conformance suite lets independent implementers verify their own nodes against all three backends.

---

## Phase 12 — Security Hardening ✓ Done

**Shipped: Q3–Q4 2026**

Phase 12 closes the concrete security gaps in the current threat model and ships the community pen-test contribution path. The normative spec for this phase is [§22 Security Hardening](/docs/spec#section-22).

- mTLS for federation peer connections; TLS 1.3 floor; URI SAN / entity_uri binding (§22.1).
- Ed25519 key rotation: dual-trust window, rotation chain integrity, transparency-log recording (§22.2).
- General-purpose audit log: 13 event types, write-ahead ordering, 90-day minimum retention (§22.3).
- Per-principal token-bucket quotas across 7 dimensions; 429 + Retry-After backpressure (§22.4).
- Federation replay-protection fuzz tests (Hypothesis) + constant-time crypto audit (§22.5).
- Container hardening: non-root UID 65532, distroless base, read-only filesystem, dropped capabilities, custom seccomp profile (§22.6).
- **Threat model** — formal STRIDE analysis per trust boundary, risk register linked to spec §§19, 20, 22; published at [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).
- **Community pen testing** — scope, safe-harbor terms, report template, and recognition model at [Community Pen-Test Handbook](./security/pen-test.md). Overview at [Security](./security/index.md).

**Phase 12 docs delta:**
- [Security section](/docs/security) — new top-level nav section.
- [mTLS Federation Transport](/docs/security/mtls) — cert provisioning, rotation, cipher policy, SAN validation, Kubernetes cert-manager recipes.
- [Key Rotation Security Runbook](/docs/security/security-key-rotation) — dual-trust window model, rotation procedure, post-rotation checklist, threat notes.
- [Audit Log & Per-Principal Quotas](/docs/security/audit-and-quotas) — `audit.read` key provisioning, event types, quota model, Prometheus metrics.
- [Community Pen-Test Handbook](/docs/security/pen-test) — in-scope surfaces, safe-harbor terms, reproducer template, severity guidance, disclosure timeline, recognition.
- [Container Hardening](/docs/operators/container-hardening) — seccomp profile, non-root image, SBOM, cosign verification, Kubernetes security context.
- [Audit & Quotas Operator Quick-Start](/docs/operators/audit-and-quotas) — operator checklist and quick setup for audit key and quota tuning.
- [Tutorial: Harden a Stigmem Deployment](/docs/tutorials/hardening-a-stigmem-deployment) — end-to-end walkthrough from default node to Phase 12 hardened posture (mTLS, key rotation, quotas, hardened container).

**What this means for operators:** Stigmem reaches the hardening posture appropriate for multi-org federation. The community pen-test path opens the protocol to external security review. The new tutorial walks the full hardening sequence end to end.

---

## Phase 13 — SDKs, Eval & Observability ✓ Done

**Shipped: Q4 2026**

Phase 13 fills the tooling gaps that block adoption at scale. The normative spec for this phase is §23 (RTBF Tombstones), §24 (Time-Travel / As-Of Queries), and §25 (Content-Addressed Fact IDs) in v1.1-draft.

- **TypeScript SDK** (`stigmem-ts`) for browser/Node agents; **Go SDK** (`stigmem-go`) for hosted-infra integrators. Both cover facts, conflicts, recall, memory cards, subscriptions, and federation.
- **Eval harness** — 79 adversarial scenarios (typo-squatting, contradiction floods, tombstone bypass, capability-token forgery, sanitizer bypass) and 400 recall probes (nDCG@10 + Recall@5). Runs in CI against all backends; independent implementations can run it against their own nodes.
- **OpenTelemetry traces** and **Prometheus metrics** (8 counters, 3 histograms, 2 gauges) with reference Grafana dashboards and Prometheus alerting rules. Plug into existing observability stacks without custom instrumentation.
- **Right-to-be-forgotten** (§23) — tombstone facts with Ed25519 cryptographic signatures, propagated across federation. Legal-hold mode preserves admin access for litigation.
- **Time-travel API** (§24) — `as_of` parameter on fact query and recall endpoints for point-in-time queries. Append-only retraction log for temporal correctness.
- **Content addressing** (§25) — facts addressable by SHA-256 content hash (CID) for deduplication, integrity verification, and external citation. Dual addressing (UUID + CID) with 12-month backfill window.
- **Quota & isolation per garden / per principal.**

**Phase 13 docs delta:**
- [TypeScript SDK Reference](/docs/sdks/typescript-sdk) — `StigmemClient` API, value constructors, error classes, bundler compatibility.
- [Go SDK Reference](/docs/sdks/go) — idiomatic Go client, functional options, mTLS support, channel-based subscriptions.
- [Tutorial: SDK Quickstart](/docs/tutorials/sdk-quickstart) — choose-your-stack walkthrough (Python / TypeScript / Go) covering assert, recall, and subscribe.
- [Observability](/docs/operators/observability) — Prometheus metrics reference, OpenTelemetry tracing setup, Grafana dashboards, alerting rules, docker-compose overlay.
- [Eval Harness](/docs/operators/eval-harness) — adversarial corpus (79 scenarios), recall benchmark (400 probes), CI integration, running against independent implementations.
- [RTBF Tombstones](/docs/guides/rtbf) — CLI and API usage, legal-hold semantics, federation propagation, signing details, operations checklist.
- [Time-Travel Queries](/docs/guides/time-travel) — `as_of` parameter, retraction data model, legal-hold admin access, retention floor configuration.
- [Content Addressing](/docs/guides/content-addressing) — CID format and computation, dual addressing, write-path deduplication, federation tamper detection, backfill monitoring.

**What this means for operators:** every major language ecosystem has a first-class SDK. Compliance teams get tombstone proofs and temporal queries. Observability stacks get native signals without custom adapters. The eval harness gives independent implementers a security and quality baseline to test against.

---

## Phase 14 — Spec v2.0

**Target: Q4 2026**

Phase 14 closes the open spec drafts and tags the stable v2.0 release.

- §19 Federation Trust → normative *(already shipped in v1.1; Phase 14 confirms no breaking changes before v2.0 tagging)*.
- §20 Recall & Graph → **normative**.
- Instruction-manifest pattern → **normative**.
- Source-trust model → **normative**.
- **Stigmem v2.0** tagged.
- **Documentation IA restructure** — operator docs, integrator docs, and spec reference separated into distinct navigation sections.
- **Migration guide v1.0 → v2.0** — breaking changes to the federation handshake, storage backend API, and recall endpoint, with before/after examples.

**What this means for operators:** v2.0 is the stable long-term target for integration. The migration guide covers exactly what to update from v1.0.

---

## What is not on this roadmap

- **A hosted offering.** The team provides reference deployments (Fly.io, Compose, Helm, systemd) so operators can run their own nodes. There is no plan to operate a multi-tenant hosted product.
- **Marketing site polish or a public launch announcement.** Deferred indefinitely.
- **A competing agent platform or orchestration layer.** Stigmem is a memory substrate — it makes existing agent frameworks, IDEs, and workflow tools more capable, not redundant.
- **An in-house compliance or GRC tool.** Stigmem provides provenance and audit primitives; compliance application logic is out of scope.

---

*This page is updated at every phase boundary. Last updated: Q4 2026 — Phase 13 complete (TypeScript SDK, Go SDK, eval harness, observability, RTBF tombstones, time-travel queries, content addressing; SDK Quickstart tutorial, 8 new/updated doc pages live). Phase 14 next.*
