# Stigmem — Federated Knowledge Fabric + Intent Protocol

[![CI](https://github.com/eidetic-labs/stigmem/actions/workflows/ci.yml/badge.svg)](https://github.com/eidetic-labs/stigmem/actions/workflows/ci.yml)
[![Conformance](https://github.com/eidetic-labs/stigmem/actions/workflows/conformance.yml/badge.svg)](https://github.com/eidetic-labs/stigmem/actions/workflows/conformance.yml)
[![PyPI version](https://img.shields.io/pypi/v/stigmem?include_prereleases&label=pypi)](https://pypi.org/project/stigmem/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Stability: preview alpha](https://img.shields.io/badge/stability-preview%20alpha-orange.svg)](#why-v090a1-and-not-v10)
[![Discord](https://img.shields.io/discord/1502847943118684331?label=discord&logo=discord&logoColor=white&color=5865F2)](https://discord.gg/Z47Re7FjjV)

> **Status: `v0.9.0a8` — preview alpha, pre-stable · Apache-2.0**
> **Repository:** [github.com/eidetic-labs/stigmem](https://github.com/eidetic-labs/stigmem)
> **Not yet recommended for production federation across organizational boundaries.** See [LIMITATIONS.md](LIMITATIONS.md) and the [retraction post](#why-v090a1-and-not-v10) for context.

Stigmem is an open specification and reference implementation for a federated knowledge fabric: a shared, persistent layer where AI agents and humans write typed, traceable facts that travel across tools, platforms, and organizations.

Every fact is an immutable record — `(entity, relation, value, source, timestamp, confidence, scope)` — with full provenance, a hybrid logical clock timestamp, and a defined expiry. Nodes can peer with each other via a signed handshake; facts replicate across scope boundaries under explicit permission. Contradictions between nodes are surfaced as first-class records, not silently overwritten.

Stigmem does **not** replace company orchestration platforms, agent runtimes, or tool protocols like MCP. It sits above them — the shared cognitive layer they all reason over.

---

## Why `v0.9.0a1` and not `v1.0`

The public version line was reset from the earlier `v1.0` announcement to `v0.9.0a1` so the release label matches the validated stability posture. Several controls our threat model identifies as required for stable production — mTLS-default federation, persistent audit log, per-principal rate limits, capability-level validation for cross-org instructions, bounded HLC skew enforcement — remain hardened-core work rather than shipped GA guarantees.

The canonical version line has been reset. **`v0.9.0a1` is the *first build* of stigmem.** Earlier version markers (`v0.2` through `v2.0`) labeled internal development checkpoints, not tagged releases anyone deployed in production. The spec *content* under those markers is real product specification — it is being reviewed section by section against the actual implementation and migrated forward into the v0.9.0 canonical structure. Only the implied chronology is being corrected.

We chose `v0.9.0a1` (PEP 440 alpha) over `v0.9.0-preview` because alpha-beta-rc has built-in iteration semantics (`a1`, `a2`, `b1`, `rc1`) and ecosystem-native sort ordering in PyPI and npm — see [ADR-019](docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md).

For the full story, read [the retraction post on dev.to](https://dev.to/offbyonce/walking-back-our-v10-announcement-resetting-to-v090a1-as-the-first-build-al0). The in-repo canonical source is preserved at [`archive/devto-stigmem-v0.9.0a1-retraction.md`](archive/devto-stigmem-v0.9.0a1-retraction.md).

Project progress notes live in [`LOG.md`](LOG.md).

---

## Security posture

Stigmem is pre-stable. Adopters should read these documents *before* integrating against the API:

- **[LIMITATIONS.md](LIMITATIONS.md)** — adopter-facing constraints, known gaps, deployment patterns that are safe vs. unsafe at the current alpha.
- **[SECURITY.md](SECURITY.md)** — vulnerability disclosure policy, supported versions, contact path.
- **[`spec/security/threat-model.md`](spec/security/threat-model.md)** — STRIDE risk register with per-risk status (Mitigated / Residual / Open / Accepted) per release.
- **[Security architecture](docs/docs/security/index.md)** (Docs site, *Secure* tab) — capability boundaries, federation trust model, prompt-injection handling per [ADR-003](docs/adr/003-prompt-injection.md).
- **Operator hardening guide** — future hardened-core work per [`ROADMAP.md`](ROADMAP.md); single-org single-node deployments are the only currently-supported deployment pattern.
- **Release-cadence runbook & rollback** — `docs/internal/release-cadence.md` (maintainer-facing) covers how releases are cut, what gets verified post-publish, and the rollback procedure if a release ships broken (PyPI yank, npm deprecate, GHCR fix-forward). Adopters who hit issues in a release: see the rollback table for what we'll do, then file an issue with `severity:high` if it warrants a yank.

A federated-memory protocol earns trust by being correct under adversarial conditions. This release is a substrate to build against and review, not a production system.

---

## AI-authorship disclosure

Stigmem is built by two contributors with heavy AI-coding assistance. We disclose this because a category whose product is trust shouldn't quietly hide where the work came from.

**Paths with deeper human review (line-by-line):**
- `spec/` — protocol specification text
- `docs/adr/` — Architecture Decision Records
- `LIMITATIONS.md`, `SECURITY.md`, `MAINTAINERS.md`, root `README.md`
- All threat-model entries (`spec/security/`, `docs/security/`)

**Paths with lighter human review (high-level direction + spot-checks):**
- `node/src/` — implementation
- `adapters/` — adapter implementations
- `sdks/` — SDK stubs
- `apps/` — UI scaffolding
- Test suites
- Documentation pages outside the spec and ADRs

This disclosure is also in [`CONTRIBUTING.md`](CONTRIBUTING.md) and the docs-site [AI authorship disclosure](docs/docs/community/ai-authorship.md). It is not a defect notice — it's a calibration aid for anyone evaluating whether to trust stigmem with their workload. Treat the lighter-reviewed paths as you would any AI-written code: verify behavior against the spec, run the conformance suite, and audit before adopting.

---

## The name

**Stigmem** = **Stigmergy** + **Memory**.

[Stigmergy](https://en.wikipedia.org/wiki/Stigmergy) (Greek *stigma* — mark; *ergon* — work) is the coordination mechanism observed in ant colonies and termite mounds: agents don't communicate directly with each other. Instead, they leave traces in a shared environment — a pheromone trail, a soil deposit — and those traces guide the behavior of future agents. The colony's intelligence emerges from the environment itself, not from any central controller.

Stigmem applies the same principle to multi-agent AI systems. Agents write typed, provenance-tagged facts into a shared substrate. Other agents — running later, on different platforms, inside different organizations — read those facts and act on them. No central coordinator, no point-to-point protocol overhead. The knowledge environment carries the coordination signal.

The **Memory** half reflects persistence and decay: facts have `valid_until` expiries and confidence scores, so the substrate stays fresh rather than accumulating stale state — just as pheromone trails fade when they're no longer reinforced.

---

## Current status

The features below are **implemented in code** but have **not yet completed adversarial validation** at v0.9.0a8. Read [LIMITATIONS.md](LIMITATIONS.md) for which deployment patterns are currently safe.

| Area | Implementation | Spec reference |
|------|--------|-------------|
| Core fact shape (`entity`, `relation`, `value`, `source`, `timestamp`, `confidence`, `scope`) | Implemented | `Spec-01-Fact-Model` |
| `valid_until`, provenance, contradiction | Implemented | `Spec-15-Fact-Semantics` |
| HTTP wire format (assert, query, retract, single-fact GET) | Implemented | `Spec-03-HTTP-API` |
| Auth: API keys, per-scope restrictions | Implemented | `Spec-02-Scopes-and-ACL`, `Spec-06-Capability-Tokens` |
| `/.well-known/stigmem` node metadata | Implemented | `Spec-03-HTTP-API`, `Spec-04-Manifests` |
| Hybrid Logical Clock (HLC) | Implemented | `Spec-01-Fact-Model`, `Spec-12-HLC-Bounded-Skew` |
| Federation: PeerDeclaration handshake (Ed25519), pull replication, scope enforcement | Implemented | `Spec-05-Federation-Trust` |
| Conflict-first-class: auto-generated conflict records, resolution API | Implemented | `Spec-15-Fact-Semantics`, `Spec-03-HTTP-API` |
| Failure modes: split-brain, malicious peer, partial failure, replay attack | Automated tests | `Spec-18-Conformance-and-Failure-Modes` |
| Entity URI scheme (`stigmem://`) | Implemented | `Spec-01-Fact-Model` |
| Entity naming rules + lint semantics (`POST /v1/lint`, `lint_scope` MCP tool) | Implemented | `Spec-01-Fact-Model`, `Spec-20-Lint-Semantics` |
| Adapter ABI (MCP, Paperclip, OpenClaw) | Implemented | `Spec-19-Adapter-ABI` |
| Decay sweep (`POST /v1/decay/sweep`, configurable TTL + confidence-decay policies) | Implemented but deferred | `Spec-X9-Decay-Semantics` |
| Synthesis (`POST /v1/synthesis`, `synthesize_scope` MCP tool) | Implemented but deferred | `Spec-X10-Synthesis` |
| Cursor-checkpoint export/import (bounded DB-loss recovery) | Implemented | `Spec-05-Federation-Trust`, `Spec-17-Schema-and-Migration` |
| N-node federation backpressure + scope propagation invariants | Implemented | `Spec-05-Federation-Trust` |
| Browser UI (human surface) | Deferred (`experimental/dashboard/`, per [ADR-002](docs/adr/002-v1-scope.md)) | — |
| Intent envelope (`goal`, `constraint`, `preference`, `handoff`) | Deferred indefinitely (`experimental/intent-envelope/`, per [ADR-001](docs/adr/001-versioning.md)) | `Spec-X8-Intent-Envelope` |

---

## Install

**Single node (Docker — recommended):**

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
docker compose up -d
```

`docker compose up` pulls pre-built multi-arch images from GHCR (`ghcr.io/eidetic-labs/stigmem-node:0.9.0a8`, signed via Sigstore cosign with attached SBOMs). The recipe pins to the version tag for reproducibility — see [the tag-selection guide](https://docs.stigmem.dev/operators/deployment/install#image-tags) for when to use `:latest`, `:edge`, or a `@sha256:<digest>` pin instead. If you're a contributor working on changes, use `docker compose up --build -d` to force a local rebuild.

Two federated nodes start immediately:

| Node | Host port | Interactive API | Node metadata |
|------|-----------|-----------------|---------------|
| `node-a` | 8765 | `http://localhost:8765/docs` | `http://localhost:8765/.well-known/stigmem` |
| `node-b` | 8766 | `http://localhost:8766/docs` | `http://localhost:8766/.well-known/stigmem` |

Key environment variables (`STIGMEM_` prefix, set in `docker-compose.yml` `environment:` block):

| Variable | Default | Purpose |
|----------|---------|---------|
| `STIGMEM_NODE_URL` | `http://localhost:8765` | Public URL included in PeerDeclarations |
| `STIGMEM_FEDERATION_ENABLED` | `false` | Enable pull replication |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | Seconds between pull cycles |
| `STIGMEM_AUTH_REQUIRED` | `true` | Require Bearer token on every request. Set `false` for local dev only |
| `STIGMEM_DB_PATH` | `stigmem.db` | SQLite database path |

→ Full environment variable reference: **[Operating Stigmem → Install](docs/docs/operators/deployment/install.md)**

**Single node (Python / uv):**

```bash
cd stigmem/node
uv run python -m stigmem_node
```

**Pre-release install via `pip`:** because v0.9.0a8 is a PEP 440 pre-release, `pip install stigmem` (default channel) will *not* pick it up. Use `--pre` to opt in to the alpha line, and pick the install scope appropriate to your role:

```bash
pip install --pre stigmem            # SDK only — most common; for apps calling a stigmem node
pip install --pre stigmem[node]      # SDK + reference node service (self-host the server)
pip install --pre stigmem[openclaw]  # SDK + OpenClaw adapter (experimental alpha connector)
pip install --pre stigmem[all]       # everything published from this repo
```

`stigmem` is a meta-package; the actual code ships under `stigmem-py` (SDK), `stigmem-node` (server), and `stigmem-openclaw` (adapter). You can install any of those directly if you'd rather skip the meta-package: `pip install --pre stigmem-py`, etc.

**Migrating from bare-metal to Docker?** See the [upgrade path guide](docs/docs/get-started/upgrade-v1.md).

## Quickstart — two nodes federating

→ **[Get started → Quickstart tutorial](docs/docs/get-started/quickstart-tutorial.md)** — zero to two-node federation in under 10 minutes.
The quickstart also includes troubleshooting notes for busy host ports, Docker
image pull failures, and inspecting a failed demo before teardown.

Quick summary:

```bash
# 1. Start two nodes (pulls signed images from GHCR; add --build for contributors)
git clone https://github.com/eidetic-labs/stigmem && cd stigmem
docker compose up -d

# 2. Federation handshake (register both directions)
docker exec stigmem-node-a-1 \
  stigmem federation register-peer \
    --local-url http://node-a:8765 --remote-url http://node-b:8765 --scopes company,public
docker exec stigmem-node-b-1 \
  stigmem federation register-peer \
    --local-url http://node-b:8765 --remote-url http://node-a:8765 --scopes company,public

# 3. Assert a fact on node-a
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -d '{"entity":"user:alice","relation":"memory:prefers","value":{"type":"string","v":"dark mode"},
       "source":"agent:settings","confidence":1.0,"scope":"company"}' | jq .

# 4. Wait ~30 s, then verify replication on node-b
curl -s 'http://localhost:8766/v1/facts?entity=user:alice&scope=company' | jq .facts
```

For automated reproducibility testing:

```bash
make demo
```

Set `DEMO_BUILD=1 make demo` if you want the demo to force-build the local
working tree instead of using the pinned GHCR image.

To see the adversarial federation path, run:

```bash
make demo-attack
```

`make demo-attack` exercises the malicious-peer rejection gate: a peer attempts
an unauthorized scope write and a source-forged write; both are rejected and
audited.

Set `DEMO_ATTACK_TRANSCRIPT=/tmp/demo-attack.json make demo-attack` to write a
small JSON transcript with the two scenarios, their expected outcomes, and the
focused acceptance gate result. The transcript intentionally excludes secrets,
tokens, and private keys.

### Run the test suite

```bash
cd stigmem/node
uv run pytest tests/ -v
```

---

## Architecture in brief

```
stigmem/
├── spec/           ← canonical specification (under review for v0.9.0a1 first-build canonicalization)
├── node/           ← reference node: FastAPI + SQLite
├── adapters/       ← adapter code (OpenClaw is experimental in v0.9.0a8; MCP deferred)
├── sdks/           ← Python and TypeScript client SDKs (Go SDK deferred)
├── experimental/   ← deferred features per ADR-002 (dashboard, additional adapters, deploy recipes, more)
└── docs/           ← Docusaurus 3 documentation site
```

See [`docs/docs/reference/architecture/`](docs/docs/reference/architecture/index.md) for the full architecture reference, or [`docs/docs/concepts/overview.md`](docs/docs/concepts/overview.md) for the conceptual entry point.

---

## What Stigmem is not

Stigmem does not compete with:
- **Agent platforms** (OpenClaw/Claude Code) — Stigmem is the shared substrate agents reason over, not an agent runtime.
- **Company orchestration** (Paperclip) — Stigmem sits *upstream* of Paperclip; the Paperclip adapter emits issue lifecycle events as Stigmem facts.
- **Tool protocols** (MCP) — MCP is the transport; the Stigmem MCP adapter ships Stigmem as an MCP server.

It fills the gap none of them fill: typed, provenance-traceable, federated, entity-scoped shared knowledge.

---

## Spec

The canonical specification lives in [`spec/`](spec/). See [`spec/README.md`](spec/README.md) for the section-by-section status table.

The spec is being reviewed and improved into the v0.9.0a1 canonical structure: core sections first, then experimental sections move to `experimental/<feature>/spec.md` per [ADR-008](docs/adr/008-experimental-gates.md) and [ADR-010](docs/adr/010-modular-specs.md). Earlier evolutionary spec files (`stigmem-spec-pre-reset.md` through `stigmem-spec-pre-reset draft.md`) move to `spec/archive/evolution/` after their content has been forward-migrated. Nothing from the spec is being deleted.

---

## Community

Real-time chat: **[discord.gg/Z47Re7FjjV](https://discord.gg/Z47Re7FjjV)**.

The Stigmem Discord is where adopters, contributors, and operators discuss installation, federation, the spec, and SDK use. Help channels are organized by topic (`#install-help`, `#usage-questions`, `#federation-help`, `#troubleshooting`); spec and contributor discussion lives under the **Development** category. Asynchronous discussion continues to happen in [GitHub Discussions](https://github.com/eidetic-labs/stigmem/discussions) — both work.

If you're already running Stigmem in production and would consider participating in the future hardened-core external operator soak, mention it in `#dev-general` or DM `@offbyonce`. We're recruiting.

For security disclosures, see [SECURITY.md](SECURITY.md) — never report vulnerabilities in Discord.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the RFC process. Short version:

1. Open an issue using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml)
2. Discuss and iterate
3. Submit a PR against the canonical spec — new sections start as draft blocks inside the relevant spec file
4. Spec changes merge per the **[ADR-001 §Contributor approval rule](docs/adr/001-versioning.md)**: two contributors *or* the founder alone, through the pre-stable hardening window.

For bugs in the reference node, use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).

Maintainers and contributors are listed in [MAINTAINERS.md](MAINTAINERS.md).

---

## Security

To report a vulnerability, use GitHub's private advisory process — **do not open a public issue**. See [SECURITY.md](SECURITY.md) for the full disclosure policy and the v0.9.0a8 security posture statement.

The full STRIDE threat model with per-release risk-register status lives at [`spec/security/threat-model.md`](spec/security/threat-model.md). See also [Security posture](#security-posture) above.

---

## License

Apache-2.0. See [LICENSE](LICENSE).
