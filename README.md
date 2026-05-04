# Stigmem — Federated Knowledge Fabric + Intent Protocol

[![Conformance](https://github.com/Eidetic-Labs/stigmem/actions/workflows/conformance.yml/badge.svg)](https://github.com/Eidetic-Labs/stigmem/actions/workflows/conformance.yml)

> **Status: v1.0 stable · Phase 7 (substrate) · Apache-2.0**
> **Repository:** [github.com/Eidetic-Labs/stigmem](https://github.com/Eidetic-Labs/stigmem)

Stigmem is an open specification and reference implementation for a federated knowledge fabric: a shared, persistent layer where AI agents and humans write typed, traceable facts that travel across tools, platforms, and organizations.

Every fact is an immutable record — `(entity, relation, value, source, timestamp, confidence, scope)` — with full provenance, a hybrid logical clock timestamp, and a defined expiry. Nodes can peer with each other via a signed handshake; facts replicate across scope boundaries under explicit permission. Contradictions between nodes are surfaced as first-class records, not silently overwritten.

Stigmem does **not** replace company orchestration platforms, agent runtimes, or tool protocols like MCP. It sits above them — the shared cognitive layer they all reason over.

---

## The name

**Stigmem** = **Stigmergy** + **Memory**.

[Stigmergy](https://en.wikipedia.org/wiki/Stigmergy) (Greek *stigma* — mark; *ergon* — work) is the coordination mechanism observed in ant colonies and termite mounds: agents don't communicate directly with each other. Instead, they leave traces in a shared environment — a pheromone trail, a soil deposit — and those traces guide the behavior of future agents. The colony's intelligence emerges from the environment itself, not from any central controller.

Stigmem applies the same principle to multi-agent AI systems. Agents write typed, provenance-tagged facts into a shared substrate. Other agents — running later, on different platforms, inside different organizations — read those facts and act on them. No central coordinator, no point-to-point protocol overhead. The knowledge environment carries the coordination signal.

The **Memory** half reflects persistence and decay: facts have `valid_until` expiries and confidence scores, so the substrate stays fresh rather than accumulating stale state — just as pheromone trails fade when they're no longer reinforced.

---

## Current status

| Area | Status | Spec section |
|------|--------|-------------|
| Core fact shape (`entity`, `relation`, `value`, `source`, `timestamp`, `confidence`, `scope`) | **Implemented** | §2 |
| `valid_until` decay, provenance, contradiction | **Implemented** | §3 |
| HTTP wire format (assert, query, retract, single-fact GET) | **Implemented** | §5.1–5.5 |
| Auth: API keys, per-scope restrictions | **Implemented** | §3.5 |
| `/.well-known/stigmem` node metadata | **Implemented** | §5.3 |
| Hybrid Logical Clock (HLC) | **Implemented** | §2.4 |
| Federation: PeerDeclaration handshake (Ed25519), pull replication, scope enforcement | **Implemented** | §6 |
| Conflict-first-class: auto-generated conflict records, resolution API | **Implemented** | §3.3, §5.9–5.10 |
| Failure modes: split-brain, malicious peer, partial failure, replay attack | **Automated tests** | §11 |
| Entity URI scheme (`stigmem://`) | **Implemented** | §2.5 |
| Entity naming rules + lint semantics (`POST /v1/lint`, `lint_scope` MCP tool) | **Implemented** | §2.6, §14 |
| Adapter ABI (MCP, Paperclip, OpenClaw) | **Implemented** | §12 |
| Decay sweep (`POST /v1/decay/sweep`, configurable TTL + confidence-decay policies) | **Implemented** | §15 |
| Synthesis (`POST /v1/synthesis`, `synthesize_scope` MCP tool) | **Implemented** | §16 |
| Cursor-checkpoint export/import (bounded DB-loss recovery) | **Implemented** | §6 |
| N-node federation backpressure + scope propagation invariants | **Implemented** | §6.7–6.8 |
| Browser UI (human surface) | In progress | — |
| Intent envelope (`goal`, `constraint`, `preference`, `handoff`) | Draft — feedback wanted | §4 |

---

## Install

**Single node (Docker — recommended):**

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
docker compose up --build -d
```

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

→ Full environment variable reference: **[docs/docs/install.md](docs/docs/install.md)**

**Single node (Python / uv):**

```bash
cd stigmem/node
uv run python -m stigmem_node
```

**Migrating from bare-metal to Docker?** See the [upgrade path guide](docs/docs/install.md#upgrade).

## Quickstart — two nodes federating

→ **[docs/docs/getting-started/quickstart.md](docs/docs/getting-started/quickstart.md)** — zero to two-node federation in under 10 minutes.

Quick summary:

```bash
# 1. Start two nodes
git clone https://github.com/Eidetic-Labs/stigmem && cd stigmem
docker compose up --build -d

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
bash scripts/quickstart-verify.sh
```

### Run the test suite

```bash
cd stigmem/node
uv run pytest tests/ -v
```

---

## Architecture in brief

```
stigmem/
├── spec/           ← canonical specification (v0.2 → v1.0 stable)
├── node/           ← reference node: FastAPI + SQLite, 74 tests
├── adapters/       ← MCP server (TypeScript), OpenClaw (Python), Paperclip (JS hook)
├── dogfood/        ← CEO memory migration scripts
└── docs/           ← Docusaurus 3 documentation site
```

See [`docs/docs/architecture/`](docs/docs/architecture/index.md) for the full architecture reference, or [`docs/docs/about/state-of-stigmem.md`](docs/docs/about/state-of-stigmem.md) for the current-state narrative.

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

Current stable version: **[`spec/stigmem-spec-v1.0.md`](spec/stigmem-spec-v1.0.md)** — §1–18 all stable; §17 Memory Garden and §18 Source Attestation promoted from v0.9-draft.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the RFC process. Short version:

1. Open an issue using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml)
2. Discuss and iterate
3. Submit a PR against the canonical spec ([`spec/stigmem-spec-v1.0.md`](spec/stigmem-spec-v1.0.md)) — new sections start as draft blocks inside the stable spec file
4. Spec changes merge with ≥2 approvals from active contributors

For bugs in the reference node, use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).

---

## Security

To report a vulnerability, use GitHub's private advisory process — **do not open a public issue**. See [SECURITY.md](SECURITY.md) for the full disclosure policy and the v1.0-rc security posture statement.

---

## License

Apache-2.0. See [LICENSE](LICENSE).
