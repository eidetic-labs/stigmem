# Stigmem — Federated Knowledge Fabric + Intent Protocol

> **Status: v0.5 implemented · v0.6-draft in progress · Apache-2.0**
> **Repository:** [github.com/Eidetic-Labs/stigmem](https://github.com/Eidetic-Labs/stigmem)

Stigmem is an open specification and reference implementation for a federated knowledge fabric: a shared, persistent layer where AI agents and humans write typed, traceable facts that travel across tools, platforms, and organizations.

Every fact is an immutable record — `(entity, relation, value, source, timestamp, confidence, scope)` — with full provenance, a hybrid logical clock timestamp, and a defined expiry. Nodes can peer with each other via a signed handshake; facts replicate across scope boundaries under explicit permission. Contradictions between nodes are surfaced as first-class records, not silently overwritten.

Stigmem does **not** replace company orchestration platforms, agent runtimes, or tool protocols like MCP. It sits above them — the shared cognitive layer they all reason over.

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
| Entity URI scheme (`stigmem://`) | Draft (v0.6) | §2.5 |
| Adapter ABI (MCP, Paperclip, OpenClaw) | In progress (Phase 4) | §12 |
| Intent envelope (`goal`, `constraint`, `preference`, `handoff`) | Draft — feedback wanted | §4 |
| Synthesis, decay UI, contradiction digests | Planned (Phase 5) | §13 |

---

## Install

**Single node (Docker):**

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
docker compose up --build -d
```

Node A starts on `http://localhost:8765`, Node B on `http://localhost:8766`.

- Interactive API docs: `http://localhost:8765/docs`
- Node metadata: `http://localhost:8765/.well-known/stigmem`

**Single node (Python / uv):**

```bash
cd stigmem/node
uv run python -m stigmem_node
```

See [node/README.md](node/README.md) for environment variable reference.

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
├── spec/           ← canonical specification (v0.2 → v0.6-draft)
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

Current working draft: **[`spec/stigmem-spec-v0.6-draft.md`](spec/stigmem-spec-v0.6-draft.md)** — §1–6, §8–11 stable; §12 Adapter ABI normative; §4 Intent Envelope draft.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the RFC process. Short version:

1. Open an issue using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml)
2. Discuss and iterate
3. Submit a PR against the active spec draft (`spec/stigmem-spec-v0.6-draft.md`)
4. Spec changes merge with ≥2 approvals from active contributors

For bugs in the reference node, use the [bug report template](.github/ISSUE_TEMPLATE/bug_report.yml).

---

## License

Apache-2.0. See [LICENSE](LICENSE).
