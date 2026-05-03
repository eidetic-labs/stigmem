# Script: Self-Hosted Stigmem Node Setup
<!-- Video 1 of 3 | Target length: ≤ 10 min | Audience: developers, node operators -->

## Video description (YouTube / project channel copy)

> Get a stigmem node running locally in under ten minutes using Docker Compose.
> We cover prerequisites, first start, health checks, asserting your first fact, and a quick tour of the interactive API docs.
>
> **Timestamps**
> [0:00] Introduction
> [0:45] Prerequisites (Docker, curl, jq)
> [1:45] Clone and start the stack
> [3:15] Health check and well-known metadata
> [4:30] Assert your first fact
> [6:15] Query it back
> [7:15] Interactive Swagger UI tour
> [8:45] Running without Docker (Python / macOS service)
> [9:30] Wrap-up and next steps

---

## Production notes

- **Recording environment:** terminal at 14 pt mono, browser at 125 % zoom, 1920×1080.
- **Screen sections:** split 60 % terminal / 40 % browser when showing Swagger UI.
- **Do not** show real API keys — use `sk-demo-key` or `dev-key` throughout.
- Each `[PAUSE]` marker = ~2 s silence for edits or b-roll cuts.

---

## [0:00] Introduction

**[SCREEN: title card — "Stigmem: Self-Hosted Node Setup"]**

> Stigmem is a federated knowledge graph for AI agents. Each fact is an immutable entity–relation–value triple, timestamped with a hybrid logical clock, and replicatable across nodes.
>
> In this walkthrough you'll get a single stigmem node — or a two-node federated pair — running on your machine in under ten minutes using Docker Compose.
>
> Let's get into it.

---

## [0:45] Prerequisites

**[SCREEN: terminal — `docker --version && docker compose version && curl --version && jq --version`]**

> You need three things installed: Docker 24 or later, Docker Compose v2 — that's the `docker compose` subcommand, not the legacy standalone binary — and `curl` plus `jq` for the API calls.

```bash
docker --version        # Docker version 26.x.x
docker compose version  # Docker Compose version v2.x.x
curl --version
jq --version
```

**[PAUSE]**

> If you're on macOS, Docker Desktop ships all of these. On Linux, install `docker-ce` and the `docker-compose-plugin` from your distro packages.

---

## [1:45] Clone and start the stack

**[SCREEN: terminal]**

> Start by cloning the stigmem repository and running `make up`.

```bash
git clone https://github.com/Eidetic-Labs/stigmem
cd stigmem
make up
```

> `make up` is a thin wrapper around `docker compose up --build -d`. It applies both `docker-compose.yml` and the dev override `compose.override.yml`, which adds debug logging and live source-mounting so any Python change inside `node/src` restarts the node within a second.

**[SCREEN: terminal — Docker build output scrolling]**

> The first build downloads the Python base image and installs dependencies — it takes about a minute. Subsequent starts are instant because the image is cached.

**[PAUSE]**

> Three services come up:
> - `node-a` on port 8765
> - `node-b` on port 8766
> - `federation-init`, a one-shot container that registers the two nodes as peers and then exits

**[SCREEN: terminal — `docker compose ps` output]**

```bash
docker compose ps
```

> Wait about fifteen seconds after `make up`, then run `docker compose ps`. You want to see `node-a` and `node-b` as `healthy` and `federation-init` as `exited (0)`. Exit code zero means peer registration succeeded.

---

## [3:15] Health check and well-known metadata

**[SCREEN: terminal — split with browser showing `/.well-known/stigmem` JSON]**

> Hit the health endpoint on each node:

```bash
curl -s http://localhost:8765/healthz | jq .
curl -s http://localhost:8766/healthz | jq .
```

> Both return `{"status": "ok"}`. Now look at the well-known metadata — this is how nodes identify themselves to federation peers:

```bash
curl -s http://localhost:8765/.well-known/stigmem | jq .
```

> The response includes `node_id`, `federation_pubkey` (an Ed25519 public key, base64url-encoded), and `spec_version`. Any peer that wants to federate with this node fetches this endpoint to verify its identity. This is defined in spec §5.3.

**[PAUSE]**

---

## [4:30] Assert your first fact

**[SCREEN: terminal]**

> Let's write our first fact. A stigmem fact has five required fields: `entity`, `relation`, `value`, `source`, and `scope`.

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      "dark mode",
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq .
```

> The response comes back with an `id`, an `hlc` — that's the hybrid logical clock tick, which looks like a Unix millisecond timestamp with a fractional part for ordering concurrent facts — and a `timestamp` in ISO 8601.

**[SCREEN: highlight `id` and `hlc` fields in the JSON output]**

> Facts are **immutable** once written. If you want to update `alice`'s preference, you assert a new fact for the same entity and relation. The node keeps all versions and the highest-confidence, most-recent fact wins queries.

**[PAUSE]**

> `scope: local` means this fact stays on this node — it won't replicate to federation peers. Use `scope: company` or `scope: public` for federable facts.

---

## [6:15] Query it back

**[SCREEN: terminal]**

```bash
curl -s 'http://localhost:8765/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'X-API-Key: dev-key' | jq '.facts'
```

> The query returns a `facts` array. Each fact includes `id`, `entity`, `relation`, `value`, `scope`, `source`, `confidence`, `hlc`, and `created_at`. You can filter by any combination of `entity`, `relation`, `scope`, and a `since` cursor timestamp.

**[PAUSE]**

> Now retract the fact by asserting a new version with `confidence: 0.0`:

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      "dark mode",
    "source":     "agent:settings",
    "confidence": 0.0,
    "scope":      "local"
  }' | jq '{id, confidence}'
```

> Confidence zero is the canonical retraction signal — the fact is never deleted, but queries filter it out by default.

---

## [7:15] Interactive Swagger UI tour

**[SCREEN: browser — `http://localhost:8765/docs`]**

> Every running node serves a full interactive Swagger UI at `/docs`. Open it in your browser. You'll see all endpoints grouped by tag: facts, federation, scopes, and health.

**[SCREEN: browser — expand `POST /v1/facts`]**

> Click any endpoint to expand it, then click "Try it out" to send a real request directly from the browser. The node is live so any fact you assert here is real.

**[SCREEN: browser — highlight `/openapi.json` link]**

> The raw OpenAPI schema is at `/openapi.json`. The stigmem docs site uses this schema to generate the interactive API reference — we'll link to that in the wrap-up.

---

## [8:45] Running without Docker

**[SCREEN: terminal]**

> If you prefer running from source — for example when developing the node itself — you can use `uv`:

```bash
cd stigmem/node
uv sync
uv run python -m stigmem_node
```

> The node starts on `http://localhost:8000` with the same API.

**[PAUSE]**

> On macOS you can also run it as a persistent LaunchAgent that starts automatically at login:

```bash
uv sync               # build the venv first
bash scripts/service-install.sh
```

> The install script generates a LaunchAgent plist, bootstraps it with `launchctl`, and polls the health endpoint to confirm the service is up. Logs go to `logs/stigmem.log`. Uninstall with `bash scripts/service-uninstall.sh`.

---

## [9:30] Wrap-up and next steps

**[SCREEN: title card with links]**

> You now have a running stigmem node. Here's what to explore next:
>
> - **Federation walkthrough** — watch video 2 in this series to see two nodes exchanging facts automatically
> - **MCP adapter** — watch video 3 to wire stigmem into Claude Code or any MCP-compatible agent
> - **API reference** — the interactive reference at `docs.stigmem.dev/docs/api-reference`
> - **Installation guide** — `docs.stigmem.dev/docs/getting-started/installation` for Kubernetes/Helm and production hardening

**[SCREEN: terminal — teardown]**

```bash
make down              # stop containers; keep data volumes
docker compose down -v # stop and wipe all data
```

> Thanks for watching. If you hit an issue, open a GitHub discussion at `github.com/Eidetic-Labs/stigmem`.

---

*End of script — estimated runtime: ~9 min 30 s*
