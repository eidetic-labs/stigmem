# Changelog

All notable changes to Stigmem are documented here.
This file covers the reference node (`stigmem-node`), Python SDK (`stigmem-py`), TypeScript SDK (`stigmem-ts`), and MCP adapter. Spec changes are in [`spec/CHANGELOG.md`](spec/CHANGELOG.md).

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Pre-release version strings follow [PEP 440](https://peps.python.org/pep-0440/) (Python artifacts) and [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html) (npm/Helm artifacts) per [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md).

---

## [Unreleased]

### Added

- **Plugin registry foundation.** Main now includes the stable 22-hook surface, typed voting/filter-chain/score-delta/fire-and-forget semantics, deterministic `HookRegistry` dispatch, manual/core handler registration, minimum `PluginManifest` and capability-restricted `PluginContext`, hook-site wiring across assertion/recall/federation/auth/migration/audit paths, registry audit/metrics plumbing, `TestPluginRegistry`, focused plugin tests, and a hook-firing benchmark gate.
- **Docs-site AI authorship disclosure.** The README and CONTRIBUTING AI-assisted authorship disclosure is now mirrored in the docs site under Community / Disclosure & policy so adopters and reviewers can find the review-calibration guidance outside the repository root.
- **ADR-010 modular spec foundation.** Core spec frontmatter stubs now live under `spec/specs/`, with generated `spec/PROTOCOL.md` composition metadata and a contract gate that fails on protocol-index drift.
- **ADR-010 experimental spec indexing.** Experimental spec files now carry `Spec-XN` frontmatter and appear in generated `spec/PROTOCOL.md`; archived monolithic snapshots point readers to the modular index.

### Changed

- Plugin infrastructure scope is now explicit: package discovery, dependency lifecycle, health polling, operator CLI, production signing/trust, plugin author/operator docs, and full plugin migration lifecycle/checksum tracking remain future alpha-series work.

---

## Pre-1.0 history note (2026-05-08)

The version markers below (`v0.2` through `v2.0`, plus `1.0.0-rc`) labeled internal development checkpoints, not tagged releases anyone deployed in production. The canonical version line of stigmem is being reset to `v0.9.0a1` as the *first build* per [ADR-001](docs/adr/001-versioning.md) and [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md). The historical entries below are preserved as the development record; they do not represent prior public releases.

---

## [0.9.0a1] — 2026-05-08

**Status:** preview alpha — pre-stable, not for production federation across organizational boundaries. See [LIMITATIONS.md](LIMITATIONS.md).

**Per-ecosystem version strings (per ADR-019):**
- PyPI / Python: `stigmem 0.9.0a1` (PEP 440) — **meta-package**: empty wheel that depends on `stigmem-py>=0.9.0a1,<1.0.0` by default. Extras: `stigmem[node]` adds the server, `stigmem[openclaw]` adds the adapter, `stigmem[all]` adds everything. Real code ships under `stigmem-py`, `stigmem-node`, `stigmem-openclaw`. The bare `stigmem` name is the convenience entry-point for adopters who want the SDK with one command (matches the convention of `redis`, `psycopg`, `elasticsearch`, `pymongo` — bare-name = client SDK).
- npm / Node:    `@eidetic-labs/stigmem-ts@0.9.0-alpha.1` (semver) — **first npm release.** Scoped under `@eidetic-labs` so all org Owners can manage the package without npm's free-tier limitation on team-bound package permissions. Root `package.json` is `private: true` (workspace root). Adopters install via `npm install @eidetic-labs/stigmem-ts`.
- Helm `appVersion`: `0.9.0-alpha.1` (semver)
- Git tag, GitHub release, prose: `v0.9.0a1` (shorthand)

### Added

- **Repository artifacts establishing the reset:**
  - `LIMITATIONS.md` at repo root — adopter-facing constraints, known gaps, deployment-pattern guidance.
  - `MAINTAINERS.md` at repo root — current maintainers and the [ADR-001 §Contributor approval rule](docs/adr/001-versioning.md).
  - `release/version-surfaces.yaml` — canonical inventory of release surfaces and their per-ecosystem spellings; consumed by `scripts/check_version_consistency.py`.
  - `scripts/check_version_consistency.py`, `scripts/validate_version_surfaces.py`, and `.github/workflows/version-consistency.yml` — CI gate preventing the version-state inconsistency that triggered the v1.0 retraction.
  - 19 ADRs committed under `docs/adr/` (per [ADR-005](docs/adr/005-docs-ia.md), [ADR-009](docs/adr/009-repo-structure.md)).
  - **README §Security posture** — at-a-glance security entry point with links to LIMITATIONS, threat-model, SECURITY.md, security architecture, and operator hardening.
  - **README §AI-authorship disclosure** — names which paths have been human-reviewed in depth and which haven't.
- **Spec section §25 — Content-addressed fact IDs (CIDs)** retained as a core feature (per [ADR-017](docs/adr/017-amendment-to-adr-011-cids-as-core.md), amending [ADR-011](docs/adr/011-cross-cutting-extraction.md)). CIDs are load-bearing for the storage-immutability stack ([ADR-016](docs/adr/016-storage-immutability-enforcement.md)) and the prompt-injection trust boundary ([ADR-003](docs/adr/003-prompt-injection.md) L2).

### Changed

- **Canonical version line reset.** `pyproject.toml`, `package.json`, `sdks/stigmem-py/pyproject.toml`, `sdks/stigmem-ts/package.json`, `node/pyproject.toml`, `adapters/openclaw/pyproject.toml`, README status banner, SECURITY.md "Applies to" line, and threat model "Applies to" line all updated to v0.9.0a1 (PEP 440) or 0.9.0-alpha.1 (semver) per their per-surface convention. The pre-reset Helm Chart.yaml files were retired in `release/version-surfaces.yaml` rather than re-stamped. `adapters/openclaw/pyproject.toml` `stigmem-py` dependency range bumped from `>=1.0.0rc1` (the never-published constraint) to `>=0.9.0a1,<1.0.0`. `adapters/openclaw` Development Status classifier dropped from "5 - Production/Stable" to "3 - Alpha" to match actual maturity.
- **LICENSE replaced** with canonical Apache-2.0 SPDX template. Verified ~10 substantive deviations from canonical Apache-2.0 in the previous LICENSE; replaced wholesale.
- **SECURITY.md** "Supported versions" table updated: `1.0.0-rc` retired; `0.9.0a1` listed as the current supported pre-release. v0.9.0a1 carries no stability guarantee — breaking changes during the v0.9.0aN alpha and v0.9.0bN beta series hardening window are expected and called out in this changelog.
- **Default install scope shrunk.** Multi-tenant, RTBF tombstones, time-travel queries, lazy instruction discovery, advanced memory-garden ACL, and source attestation move to `experimental/` as opt-in plugins per [ADR-011](docs/adr/011-cross-cutting-extraction.md). The default install matches the v1.0 critical-path scope from [ADR-002](docs/adr/002-v1-scope.md). Operators who need experimental features install them via the plugin system.
- **Spec content under earlier version markers preserved.** The protocol-spec content from `stigmem-spec-v0.2.md` through `stigmem-spec-v2.0.md` is being reviewed section-by-section against the actual implementation and migrated forward into the v0.9.0a1 canonical structure. Earlier evolutionary spec files move to `spec/archive/evolution/` after their content has been forward-migrated. Nothing is being deleted.

### Security

- **Threat model status header** updated to v0.9.0a1 posture. Risks the original v1.0 announcement claimed mitigated but had not (mTLS-default federation, persistent audit log, per-principal rate limits, capability validation, bounded HLC skew) are now correctly listed as Open or Residual, scheduled for the v0.9.0bN beta series per [`ROADMAP.md`](ROADMAP.md).
- **R-23** (admin-level storage tampering / fact mutation) added to the risk register; mitigation is the [ADR-016](docs/adr/016-storage-immutability-enforcement.md) L1–L5 storage-immutability stack, scheduled for the v0.9.0bN beta series.
- **No CVE-class fixes in this release.** This is a posture reset, not a security-patch release.

### Deprecated

- **No PyPI deprecation of the canonical packages needed.** Audit on 2026-05-08 confirmed `stigmem 1.0.0rc1` was never actually published to PyPI; the canonical `stigmem` name was unclaimed before the v0.9.0a1 first publish.

- **`stigmem-openclaw` 1.0.3 and 1.0.5 are yanked** (PEP 592). Both versions declared `stigmem-py>=1.0.0rc1` as a hard dependency; `stigmem-py 1.0.0rc1` was never published, so both adapter versions were end-to-end **uninstallable** since publish (verified 2026-05-09 via `uv pip install --dry-run stigmem-openclaw==1.0.5` — fails with "stigmem-py was not found in the package registry"). The retraction-narrative concern that motivated the version reset — declaring maturity not yet earned — applies as much to these adapter publishes as it did to the v1.0 announcement; the yanks correct the record. Pinned installs of `==1.0.3` or `==1.0.5` continue to resolve to those versions (PEP 592 yank does not remove); new resolutions skip them. **`stigmem-openclaw 0.9.0a1`** is the first version that is actually installable.
- **No npm package was previously published**, so there is nothing to deprecate on npm. `@eidetic-labs/stigmem-ts@0.9.0-alpha.1` is the **first** npm release of the TypeScript SDK; it ships in PR 0 alongside the PyPI release.

### Stability commitment

`v0.9.0a1` carries **no stability guarantee**. Wire format, public Python API, and SDK contracts may change during the `v0.9.0aN` alpha and `v0.9.0bN` beta series hardening windows. Stability commitments begin at `v1.0.0` GA, after a 30-day external-operator soak per [ADR-001](docs/adr/001-versioning.md). Pin to specific pre-release versions; auto-upgrade is not safe.

### Current state after v0.9.0a1

The following changes have landed on `main` after the v0.9.0a1 first build and are queued for the next alpha release:

- **Plugin registry foundation.** Core now has the 22-hook registry foundation required by ADR-011. Remaining plugin infrastructure work includes package discovery, dependency lifecycle, health polling, operator CLI, production signing/trust, plugin author/operator documentation, and full plugin migration lifecycle/checksum tracking.
- **Deferred-feature extraction path.** The next alpha releases continue the C1 plugin architecture: lazy instruction discovery first, then time-travel, tombstones, memory-garden advanced ACL, source attestation, and multi-tenant isolation. CIDs remain core per ADR-017.
- **Large-file refactors.** The major `cli.py`, federation-route, and facts-route split work has landed on `main`; it is no longer a blocker for the next alpha.
- **Quality ratchets.** Lint-baseline tightening, coverage lift, and complexity cleanup remain active quality-improvement tracks for the alpha series.
- **Published-artifact follow-ups.** The live retraction-post URL, TypeScript SDK README, npm dist-tag convention, ClawHub skill naming/versioning notes, GHCR `latest` tag policy, Python SDK version literal, and `stigmem-node` wheel migration packaging fix are all tracked for pickup in the next alpha artifacts where applicable. The v0.9.0a1 registry artifacts themselves remain immutable.

---

## Historical development checkpoints (preserved as record, not prior releases)

The entries below labeled `v0.2` through `v2.0` and `1.0.0-rc` documented internal development checkpoints. They are preserved here as the development record. Per [ADR-001](docs/adr/001-versioning.md) and [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md), the canonical version line of stigmem begins at `v0.9.0a1` above.

---

## [2.0.0] — 2026-05-05

**Spec:** [v2.0](spec/stigmem-spec-v2.0.md) — §19–§25 promoted to normative.

### Added

- **Federation trust (§19)** — org manifest signing (Ed25519 + RFC 8785 JCS), transparency log integration (Rekor), capability tokens with 6 verbs and 90-day expiry, source-trust scoring, quarantine garden, recall-time content sanitizer.
- **Recall & graph (§20)** — materialized `entity_edges` graph index, vector embeddings via `sqlite-vec` (nomic-embed-text-v1.5 default, 768-dim), hybrid recall pipeline (BM25 + ANN + graph BFS + MMR packing), memory cards (per-entity 4000-token summaries), subscriptions with webhook delivery, causal/derivation links (`derived_from` DAG).
- **Lazy instruction discovery (§21)** — boot stub (≤500 tokens), instruction manifest (≤1000 tokens), `recall_instruction` tool contract, task-type preloads with `guarantee_load`, discovery audit (Recall@k, Hit@k, miss-rate), 5-stage file → stigmem migration, `stigmem instruction migrate` CLI.
- **Security hardening (§22)** — mTLS federation transport (TLS 1.3 floor), Ed25519 key rotation (90-day dual-trust period), structured audit log (13 event types, write-ahead, 90-day retention), per-principal token-bucket quotas (7 dimensions, HTTP 429), replay protection (±5 min window + nonce cache), container baseline (distroless, non-root, seccomp).
- **RTBF tombstones (§23)** — `TombstoneRecord` shape with signed `entity_uri` + scope suppression, recall-time filter (direct + graph reference + memory card), federation propagation with signature verification, `TombstoneRevocation` for legal holds, `GET /v1/federation/tombstones` poll route.
- **Time-travel queries (§24)** — `as_of` parameter on `/v1/recall` and `/v1/facts`, fact visibility at time T, append-only `fact_retractions` log, retroactive tombstone suppression, `legal_hold: true` preserves facts for admin `as_of` access, `tombstone_notices` response annotation.
- **Content-addressed fact IDs (§25)** — CID format (`sha256:` + hex SHA-256 of RFC 8785 canonical body over 6 fields), `fact_cid_aliases` table for dual UUID/CID addressing, 12-month migration window, federation tamper detection (`cid_mismatch` rejection), `stigmem backfill-cids` CLI, `POST /v1/facts/:id/verify-cid` integrity check.
- **Storage backend trait (pre-reset)** — `StorageBackend` abstraction, `LibSQLBackend` for Turso/libSQL embedded-replica, `STIGMEM_STORAGE_BACKEND` env var, backend-parameterized test runner.
- **Conformance vectors** — v2.0 wire-format vectors for §19–§25 in `data/conformance/v2.0/`.
- **Migration guide** — `docs/docs/migration/v1-to-v2.md` with breaking-change matrices, cutover order, and rollback notes.

### Changed

- OpenAPI spec version bumped to 2.0.0.
- `FactRecord` extended with `cid`, `derived_from`, `attestation_chain`, `source_trust` fields.
- Retraction semantics: `confidence = 0.0` in-place retained for live-query compat; authoritative retraction timestamp now in `fact_retractions` table.
- Documentation site information architecture restructured for §19–§25 content.

### Migration

- **013a** — `tombstones` + `tombstone_revocations` tables.
- **013b** — `facts.cid` column + `fact_cid_aliases` table.
- **013c** — `fact_retractions` append-only log.
- Apply order: 013a → 013c → 013b (foreign-key dependencies).
- Run `stigmem backfill-cids` after migrations to populate CIDs for pre-v2.0 facts.

### Breaking

- Federation requires mTLS (TLS 1.3+) and org manifests — plaintext peer connections rejected.
- Mixed v1.x/v2.0 federation is not supported; all peers must upgrade together.
- `STIGMEM_EMBED_DIMENSIONS` is immutable after first embedding write; changing requires full re-index.
- Graph depth capped at 3 (`depth > 3` returns HTTP 400 `graph_depth_exceeded`).

---

## [Unreleased — pre-reset] — Instruction migration + lazy instruction discovery (§21)

### Added

- **`stigmem instruction migrate` CLI** — converts markdown instruction files into atomic
  `instruction:content` facts and publishes a lazy-loaded manifest.  Supports `--role` and
  `--skill` scope selectors, `--dry-run`, `--yes`, and `--db` for local idempotency checks.
- **Instruction manifest API** (`PUT /v1/agents/{agent_id}/instruction-manifest`) — stores
  a versioned manifest of instruction units with load triggers (intents, keywords, task types)
  and token estimates.  Each publish supersedes the previous manifest rather than updating
  it in place.
- **`recall-instruction` endpoint** (`POST /v1/agents/{agent_id}/recall-instruction`) —
  three-phase lazy retrieval: hint resolution → BM25-ranked retrieval → guaranteed units.
  Returns a token-budget-bounded list of instruction chunks with an `audit_token` for
  downstream usage logging.
- **Discovery audit** — `POST /v1/instruction/audit` closes the audit loop; the
  `instruction_audit` table records agent, intent, loaded/used/missed chunks per recall call.
- **`stigmem audit discovery` CLI** — prints Recall@k, Hit@k, and miss-rate metrics for an
  agent from the local `instruction_audit` table.
- **Tombstone semantics** — units removed between migration runs receive `TOMBSTONE` action;
  their manifest entries are dropped while the underlying facts are preserved for audit history.
- **Docs** — Instruction Migration guide (`docs/docs/guides/instruction-migration.md`);
  lazy-instruction endpoint reference in `docs/docs/api-reference/index.md`.

---

## [Unreleased — pre-reset] — Storage adapter trait + libSQL/Turso backend

### Added

- **`StorageBackend` trait** (`node/src/stigmem_node/storage/`) — abstract seam
  covering connection lifecycle, transaction semantics, migration runner, and
  snapshot export/import hooks.  All new persistence backends implement this
  interface; no changes required in route handlers.
- **`SQLiteBackend`** — existing SQLite path refactored to implement
  `StorageBackend`.  Behaviour is identical to pre-trait deployments.
- **`LibSQLBackend`** — libSQL / Turso adapter implementing the trait.
  Supports embedded-replica mode (local file + Turso sync URL).  Drop-in for
  Fly.io persistent volumes.
- **`STIGMEM_STORAGE_BACKEND`** env var — `"sqlite"` (default) or `"libsql"`.
- **`STIGMEM_LIBSQL_URL`** — Turso database endpoint
  (e.g. `libsql://my-db.turso.io`).  Required when backend is `libsql`.
- **`STIGMEM_LIBSQL_AUTH_TOKEN`** — Turso auth token (from
  `turso db tokens create`).
- **`libsql` optional dependency group** — `pip install 'stigmem-node[libsql]'`
  installs `libsql-experimental>=0.3`.
- **Backend-parameterized test runner** — `pytest --backend=libsql` runs the
  full conformance suite against the libSQL backend.  Tests auto-skip when
  `libsql-experimental` is not installed.

### Changed

- `db.py` — `db()`, `apply_migrations()`, `get_or_create_federation_keypair()`,
  and `get_or_create_node_id()` all delegate to `make_backend()`.  The module-
  level `settings` attribute is still the patch point for test fixtures.

### Migration

- No schema changes.  Existing SQLite databases continue to work without any
  action.  To switch to Turso, set `STIGMEM_STORAGE_BACKEND=libsql`,
  `STIGMEM_LIBSQL_URL`, and `STIGMEM_LIBSQL_AUTH_TOKEN`, then run
  `stigmem migrate` to apply pending migrations against the new backend.

---

## [1.0.0-rc] — 2026-05-03

**Spec:** v1.0 stable (see [spec/CHANGELOG.md](spec/CHANGELOG.md#v10--2026-05-03--stable))

### Added

- **Multi-tenant scoping** — `tenant_id` column on facts + indexes; `X-Stigmem-Tenant` header enforced on all write/read routes; tenant-isolated query path (`?scope=tenant:…`).
- **Billing hooks** — `POST /v1/admin/billing/events` webhook emitter; `BillingEventKind` registry (`fact_assert`, `garden_read`, `synthesis_run`); configurable endpoint + HMAC secret via `STIGMEM_BILLING_*` env vars.
- **Memory Garden** (§17 stable) — Named ACL'd partitions; `garden_id` on `FactRecord`; admin/writer/reader role model; ACL enforced at read time.
- **Source Attestation** (§18 stable) — `entity_uri` binding on API keys; three enforcement modes (`enforce|warn|off`); `attested` field on `FactRecord`; attestation audit log (`GET /v1/auth/audit`).
- **Agent keypairs** — Ed25519 key generation via `POST /v1/auth/keys`; key rotation and revocation endpoints.
- **OIDC SSO role gate** — `STIGMEM_OIDC_*` env vars; JWT validation middleware; role-claim mapping to `admin|writer|reader`.
- **Curator dashboard** — Next.js 14 single-page app at `apps/dashboard`; fact browser, garden manager, audit log viewer.
- **Five connector adapters** — Letta, Gemini, OpenAI-tools, Cognee, and Zep adapters under `adapters/`; each ships its own `pyproject.toml` for isolated installs.
- **MCP adapter** (`adapters/mcp`) — `assert_fact`, `query_facts`, `synthesize_scope`, `lint_scope`, `decay_scope` tools; transport-agnostic; versioned at `1.0.0-rc`.
- **Conformance CI gate** — `conformance.yml` workflow; runs the full v1.0 vector suite on every push to `main` and on PRs touching `node/`, `spec/`, `data/conformance/`; zero skips enforced.
- **Docker Compose one-click install** — `docker-compose.yml` with node + Postgres; `make up` / `make down` targets; health-check probe.
- **Helm chart stub** — `charts/stigmem/` with `values.yaml`, `Chart.yaml`, and node deployment template; installable via `helm install`.
- **Docusaurus 3 documentation site** (`docs/`) — Getting Started, Concepts, API Reference (OpenAPI), Architecture diagrams, Federation tutorial, Deployment guide, Conformance guide, Security posture page, v1.0 upgrade guide.
- **Decay Semantics** (§15) and **Synthesis** (§16) — `POST /v1/decay/sweep`, `POST /v1/synthesis`; MCP tools; already stable in v0.9, now documented end-to-end.
- **Lint API** (§14) — `POST /v1/lint`; four lint checks; `lint_scope` MCP tool.
- **Fuzzy entity resolver** (§2.6.6) — semantic alias matching on entity lookup.
- **Async lint/decay job APIs** (§14.5/§15.4) — background job handles with `GET /v1/jobs/:id`.

### Changed

- Spec promoted from v0.9-draft to **v1.0 stable**; all §§1–18 normative.
- `IntentEnvelope` (§4) deferred indefinitely; retained as non-normative appendix.
- Example URIs normalized to `company.example` domain across all test fixtures.
- Per-adapter `pyproject.toml` added for unified pytest discovery.

### Security

- All Python dependencies upgraded; `pip-audit` reports zero known CVEs.
- All TypeScript/Node dependencies upgraded; `npm audit` reports zero vulnerabilities.
- Zero unaddressed Dependabot alerts on the `main` branch.
- Security posture statement published at `docs/docs/reference/security.md`.
- `bandit` static analysis clean on the `node/` package.

### Migration

- Run migration 004 (gardens table) and migration 005 (api_keys extension + attestation_audit) before starting the node. Both are idempotent.
- Set `STIGMEM_TENANT_HEADER_REQUIRED=true` if you want tenant isolation enforced at the ingress layer.
- See the [v1.0 upgrade guide](docs/docs/getting-started/upgrade-v1.md) for the full migration checklist.

---

## [0.9.0] — 2026-04

**Spec:** v0.9-draft

### Added

- Memory Garden primitive (`OIDC exchange bridge`; `garden_id` on facts; garden CRUD routes §5.14–§5.19).
- Source Attestation draft (`entity_uri` on API keys; `attested` field; enforcement modes draft).
- Scope propagation invariants (§6.8): `company`-scoped facts MUST NOT be re-federated.
- N-node backpressure header `X-Stigmem-Replication-Lag` (§6.7).

---

## [0.8.0] — 2026-03

**Spec:** v0.8 stable

### Added

- Decay Semantics (§15): `POST /v1/decay/sweep`; configurable TTL + confidence-decay policies; `DecayPolicy` registry.
- Synthesis (§16): `POST /v1/synthesis`; confidence-weighted snapshot.
- §§1–14 promoted to stable.

---

## [0.4.0] — 2025-11

**Spec:** v0.4

### Added

- Federation protocol (§6): two-node federation, HLC replication, Ed25519 peer tokens.
- Lint API (§14): `POST /v1/lint`; four lint checks.
- Per-scope API key restrictions.
- `PATCH /v1/facts/:id/confidence` retraction; `GET /v1/facts/:id` single-fact route.

---

## [0.2.0] — 2025-09

**Spec:** v0.2 initial

### Added

- Atomic fact shape: `(entity, relation, value, source, confidence, scope, timestamp, valid_until?)`.
- `text` FactValue type.
- Reification pattern (`stigmem:rel:` prefix).
- Federation stub (RFC only).
- API key auth stub.
