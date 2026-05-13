---
title: Features
sidebar_label: Features
sidebar_position: 1
description: What Stigmem does today in v0.9.0a1 — feature status table calibrated to ADR-002 v1 critical-path scope.
---

# Features

*Audience: anyone evaluating, integrating, or operating Stigmem.*

Stigmem is an open, federated knowledge protocol — a layer where AI agents and humans store typed, traceable facts that travel across tools, platforms, and organizations. Each fact is an immutable record `(entity, relation, value, source, timestamp, confidence, scope)` written once, queryable forever, with full provenance and a defined expiry.

**This page describes v0.9.0a1.** The canonical version line of stigmem begins at `v0.9.0a1` per [ADR-001](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/001-versioning.md) + [ADR-019](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). Earlier version *markers* (`pre-reset`, `v1.1`, `v2.0`) labeled internal development checkpoints, not tagged releases. Many features that earlier docs described as "Stable" were deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md) — the v1 critical-path scope cut. Those features remain in the codebase under [`experimental/<feature>/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental) per [ADR-011](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/011-cross-cutting-extraction.md), gated, off by default.

---

## How to read this page

| Status         | Meaning                                                                    |
|----------------|----------------------------------------------------------------------------|
| **Stable**     | Spec section normative in v0.9.0a1; in core; no breaking changes within v0.9.0a series wire-format scope. |
| **Preview**    | Shipped as part of v0.9.0a1 with no stability guarantee; pin to specific versions. |
| **Experimental** | Feature artifact lives under `experimental/<feature>/`; opt-in plugin extraction happens across the v0.9.0a2..a8 series per ADR-011; not in default install. |
| **Deferred**   | Code exists but is not part of the v1 critical-path; lives in `experimental/` with `STATUS.md` per [ADR-008](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). |

**No calendar dates.** Stigmem is phase-gated, not time-gated. Phase progression is documented in [ROADMAP.md](https://github.com/Eidetic-Labs/stigmem/blob/main/ROADMAP.md).

> **Why pick Stigmem over a vector-RAG product?** Stigmem retrieves *typed atomic facts*, not opaque chunks. Each embedding has an explicit `(entity, relation, value)` contract. Recall in v0.9.0a1 covers basic typed-fact retrieval; advanced recall (graph BFS, vector embeddings, MMR packing, memory cards) is deferred per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md) and ships incrementally as plugins. Read the spec at [spec/stigmem-spec-v0.9.0a1.md](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md).

---

## Core memory model (v0.9.0a1 critical path)

| Capability                          | Status     | Spec      |
|-------------------------------------|------------|-----------|
| Immutable typed facts (entity, relation, value, source, timestamp, confidence, scope) | Stable | §2, §3    |
| Scope enforcement (`local` / `team` / `company` / `public`) | Stable | §3.5      |
| Confidence (`valid_until`, retraction) | Stable | §3        |
| Conflict surfacing & resolution     | Stable     | §6.3      |
| Entity naming rules                 | Stable     | §2.5–§2.6 |
| Lint semantics                      | Stable     | §14       |
| Content-addressed fact IDs (CIDs)   | Stable in core ([ADR-017](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/017-amendment-to-adr-011-cids-as-core.md)) | §25 |

## Recall (v0.9.0a1 critical path)

| Capability                          | Status     | Spec   |
|-------------------------------------|------------|--------|
| `POST /v1/recall` basic typed-fact retrieval | Stable | §6   |
| `query_facts` operation             | Stable     | §3     |
| `assert_fact` operation             | Stable     | §3     |

## Federation (v0.9.0a1 critical path)

| Capability                          | Status     | Spec   |
|-------------------------------------|------------|--------|
| Two-node mTLS federation (TLS 1.3 floor, SAN ↔ entity_uri binding) | Stable | §22.1 |
| Ed25519 signed manifests at `/.well-known/stigmem-manifest.json` | Stable | §19 |
| Capability tokens (≤90d, Ed25519, verb+object validated at admission) | Stable | §19 |
| Bounded HLC skew + per-peer drift tracking | Targeted v0.9.0bN beta series (R-19) | §22.5 |
| Quarantine garden (federation inbound writes) | Stable | §19   |
| Pull replication                    | Stable     | §6     |

## Authentication & authorization (v0.9.0a1 critical path)

| Capability                          | Status     | Spec   |
|-------------------------------------|------------|--------|
| API-key authentication (per-scope)  | Stable (Argon2id for new keys; v0.9.0a1 SHA-256 rows rehash on successful use per [ADR-007](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/007-argon2id.md)) | §3.5 |
| Enforced API key max-age (default 90d) | Stable | §22.2 |
| Per-principal token-bucket rate limits (7 dimensions) | Stable | §22.4 |
| Capability-based instruction handling (`interpret_as`) | Targeted v0.9.0bN beta series ([ADR-003](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/003-prompt-injection.md)) | §3 |

## Observability (v0.9.0a1 critical path)

| Capability                          | Status     | Spec   |
|-------------------------------------|------------|--------|
| WAL-ordered audit log (14 event types, 90-day retention) | Stable | §22.3 |
| Prometheus metrics (node health, request rates, quotas, federation peer status) | Stable | §22.3 |

## Storage (v0.9.0a1 critical path)

| Capability                          | Status     |
|-------------------------------------|------------|
| SQLite backend                      | Stable     |
| SQLCipher at-rest encryption (opt-in) | Stable   |

## Embedding (v0.9.0a1 critical path)

| Capability                          | Status     |
|-------------------------------------|------------|
| Local `nomic-embed-text-v1.5` (default, offline) | Stable |

## SDKs

| SDK                                 | Status     |
|-------------------------------------|------------|
| Python SDK (`stigmem-py`)           | Stable (sole fully-supported SDK in v0.9.0a1 per ADR-002) |
| TypeScript SDK (`@eidetic-labs/stigmem-ts`) | Preview (published as part of v0.9.0a1; pin to specific versions) |
| Go SDK (`stigmem-go`)               | Deferred to `experimental/sdk-go/` |

## Adapters

| Adapter                             | Status     |
|-------------------------------------|------------|
| OpenClaw (`stigmem-openclaw`)       | Alpha evaluation only — published in v0.9.0a1, with copy/framing corrections queued for v0.9.0a2 and safety hardening/audit closure pending the v0.9.0aN/beta hardening path per [ADR-002](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/002-v1-scope.md) |
| MCP adapter                         | Deferred (`stigmem-mcp` at v0.4.0; not aligned to v0.9.0a1; lives in `adapters/mcp/`) |
| Obsidian / Obsidian-plugin          | Deferred to `experimental/obsidian-adapter/` |
| Letta, Zep, Cognee, Gemini, OpenAI-tools, Paperclip | Deferred to `experimental/<adapter>-adapter/` |

## Operations (v0.9.0a1 critical path)

| Capability                          | Status     |
|-------------------------------------|------------|
| Docker Compose reference deployment (`make demo`, `make demo-attack`) | Stable |
| Container hardening (distroless, non-root UID, read-only fs, seccomp) | Stable |
| Helm / Kubernetes                   | Deferred to `experimental/deploy-helm/` |
| Fly.io / systemd / Grafana / PaaS configs | Deferred to `experimental/deploy-*/` |

## Plugin infrastructure (alpha-series foundation)

| Capability                          | Status     |
|-------------------------------------|------------|
| Stable 22-hook registry surface     | Landed on main after v0.9.0a1; queued for the next alpha artifact refresh |
| Typed hook semantics                | Landed — voting, filter-chain, score-delta, fire-and-forget |
| Manual/core handler registration    | Landed — deterministic ordering with minimum manifest/context/capability APIs |
| Hook-site wiring                    | Landed across assertion, recall, federation, auth, migration, and audit paths |
| Registry observability and tests    | Landed — audit/metrics plumbing, test registry helpers, and hook-firing benchmark gate |
| Entry-point discovery, lifecycle, health polling, operator CLI | Remaining alpha-series infrastructure work |
| Production signing/trust and author/operator plugin docs | Remaining alpha-series infrastructure work |

## Experimental & deferred features

The following features are in the codebase under [`experimental/<feature>/`](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental) but are **not in v0.9.0a1's default install**. Across the v0.9.0a2..a8 alpha series, cross-cutting features are extracted into opt-in experimental plugin packages per [ADR-011](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/011-cross-cutting-extraction.md). That alpha extraction is not ADR-008 graduation; graduation into the supported surface happens later, after the [ADR-008](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/008-experimental-gates.md) five-gate process.

| Feature                             | Spec § | alpha extraction target |
|-------------------------------------|--------|----------------|
| Lazy instruction discovery          | §21    | v0.9.0a2 |
| Time-travel `as_of` queries         | §24    | v0.9.0a4 |
| RTBF tombstones                     | §23    | v0.9.0a5 |
| Memory garden — advanced ACL        | §17 advanced | v0.9.0a6 |
| Source attestation                  | §18    | v0.9.0a7 |
| Multi-tenant isolation              | (cross-cutting) | v0.9.0a8 |
| §20 Recall & Graph (vector embeddings, MMR, memory cards, subscriptions) | §20 | the v0.9.0aN alpha series |
| Decay sweep                         | §15    | Deferred (commercial path) |
| Synthesis                           | §16    | Deferred (commercial path) |
| OIDC SSO                            | —      | the v0.9.0aN alpha series |
| PostgreSQL backend, libSQL/Turso    | —      | Deferred (operator-validated demand) |
| Cloud embedding                     | —      | Deferred (R-20 accepted) |
| Curator dashboard                   | —      | Deferred |
| Billing hooks                       | —      | Deferred (commercial path) |
| Async lint/decay job APIs           | —      | Blocked on lint/decay extraction |

See the full deferred-features list at [Experimental & Deferred Features](../reference/experimental-features.md).

## v0.9.0a1 architecture in flight (Option A acknowledgment)

The v0.9.0a1 default install ships with feature-specific code in `node/src/stigmem_node/` for several deferred features (`tombstones.py`, `instruction_migrate.py`, `card_materializer.py`, `source_trust.py`, etc.). The routes are mounted but the features are dormant unless explicitly configured. Per [ADR-019](https://github.com/Eidetic-Labs/stigmem/blob/main/docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md) iteration semantics, each v0.9.0aN extracts one cross-cutting feature into a plugin per ADR-011's C1 plugin architecture; after v0.9.0a8, default install will be true to ADR-011's commitment.

Main now includes the hook-registry foundation and stable 22-hook surface, with manual/core handler registration, minimum manifest/context/capability APIs, hook-site wiring, registry observability, test helpers, and benchmark coverage. External plugins are not yet installable from package entry points, and the deferred features listed below have not yet been extracted into plugin packages.

See [LIMITATIONS.md §11 — v0.9.0a1 architecture in flight](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md) for the full architectural-gap acknowledgment.

---

## What's coming next {#whats-coming-next}

The phase progression is in [ROADMAP.md](https://github.com/Eidetic-Labs/stigmem/blob/main/ROADMAP.md). At a high level:

1. **v0.9.0a2 through v0.9.0a8** — incremental plugin extraction per ADR-011 (lazy-instruction-discovery → CIDs as core → time-travel → tombstones → memory-garden-acl → source-attestation → multi-tenant).
2. **v0.9.0bN (the v0.9.0bN beta series)** — capability redesign per ADR-003, federation hardening, OpenClaw safety, modular spec migration per ADR-010, storage immutability stack per ADR-016, 30-day external operator soak.
3. **v1.0.0-rcN → v1.0.0 (the v1.0.0rcN release-candidate series)** — Sigstore-signed releases, reproducible builds, SBOM, 3+ external operators in production. Wire format frozen.

---

## Out of scope — explicit non-targets

- **A hosted/SaaS Stigmem product.** Reference deployments only; operators run their own nodes.
- **A competing agent runtime** to OpenClaw / Claude Code / LangChain etc.
- **A multi-agent orchestration layer.** Stigmem is a memory substrate — it makes existing agent frameworks, IDEs, and workflow tools more capable, not redundant.
- **An in-house GRC / compliance product.** Stigmem provides provenance primitives; compliance application logic is out of scope.
- **A vertical agent product** (support agent, bookkeeping agent, etc.) until post-v1.0.0.
- **A chatbot of any kind.**

---

*This page is regenerated each release to reflect actual ship-state. The previous "Spec v2.0 — in flight" framing was retired during the v0.9.0a1 reset. For the development history, see [`spec/EVOLUTION.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/EVOLUTION.md).*
