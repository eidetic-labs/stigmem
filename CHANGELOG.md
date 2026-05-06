# Changelog

All notable changes to Stigmem are documented here.
This file covers the reference node (`stigmem-node`), Python SDK (`stigmem-py`), TypeScript SDK (`stigmem-ts`), and MCP adapter. Spec changes are in [`spec/CHANGELOG.md`](spec/CHANGELOG.md).

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- **Storage backend trait (Phase 8)** — `StorageBackend` abstraction, `LibSQLBackend` for Turso/libSQL embedded-replica, `STIGMEM_STORAGE_BACKEND` env var, backend-parameterized test runner.
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

## [Unreleased] — Phase 10 — Instruction migration + lazy instruction discovery (§21)

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
  Phase 10 endpoint reference in `docs/docs/api-reference/index.md`.

---

## [Unreleased] — Phase 8 — Storage adapter trait + libSQL/Turso backend

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
