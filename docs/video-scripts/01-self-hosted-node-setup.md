# Script 1 — Self-Hosted Node Setup

**Target duration:** ~9 min 30 s  
**Audience:** Developer setting up stigmem locally for the first time  
**Format:** Screen-recording, terminal + browser, narrated  

---

## YouTube / channel description block

```
stigmem — Self-Hosted Node Setup (v1.0)

Get a stigmem node running locally in under 10 minutes.
Covers: clone, start, health check, asserting your first fact, querying, and teardown.

Timestamps:
0:00 — Intro and prerequisites
1:30 — Clone and start the node
3:00 — Verify the node is healthy
4:30 — Assert your first fact
5:30 — Query facts back
6:15 — Retract a fact and filter by time
7:30 — Swagger UI tour
8:30 — Teardown
9:00 — What's next

GitHub: https://github.com/eidetic-labs/stigmem
Docs: https://stigmem.dev/docs
```

---

## Production notes

- Resolution: 1920×1080, terminal font size ≥ 16 pt
- Terminal: dark background, high-contrast text
- Mask or substitute any real API keys before recording
- Pause on command output for at least 2 s before continuing narration
- Browser segments: zoom to 125 % for Swagger UI

---

## Script

### [0:00] Intro and prerequisites

**[Screen: docs landing page or blank terminal]**

> "Welcome to stigmem. In this video I'll show you how to run a stigmem knowledge-graph node on your own machine from scratch — install, start, assert your first fact, and tear it all down."

> "You'll need Docker 24 or later, Docker Compose v2, and the standard curl and jq utilities. That's it — no Python needed for the Docker path."

**[Screen: show version checks in terminal]**

```bash
docker --version
docker compose version
curl --version
jq --version
```

> "If any of those aren't installed, the links in the description have you covered."

---

### [1:30] Clone and start the node

**[Screen: terminal]**

> "Clone the repo and start the node with a single make command."

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
make up
```

> "That runs `docker compose up --build -d` which builds and starts two services: `node-a` on port 8765 and `node-b` on 8766. For this video we're focused on `node-a` as our primary node."

> "The first build pulls and compiles dependencies — subsequent starts are much faster."

**[Wait for build to complete, show output]**

---

### [3:00] Verify the node is healthy

**[Screen: terminal]**

> "Once the build finishes, check that both services are running and healthy."

```bash
docker compose ps
```

> "You want to see both `node-a` and `node-b` in the `healthy` state. If they're still starting, wait a few seconds and run it again."

> "Let's confirm the API is responding directly."

```bash
curl -s http://localhost:8765/healthz | jq .
```

Expected output:
```json
{"status": "ok"}
```

> "And the well-known discovery endpoint — this is what other nodes use to verify our identity."

```bash
curl -s http://localhost:8765/.well-known/stigmem | jq '{node_id, federation_pubkey}'
```

> "The `node_id` is the node's stable identifier in the federation, and `federation_pubkey` is the Ed25519 public key used to authenticate signed peer declarations — more on that in the federation video."

---

### [4:30] Assert your first fact

**[Screen: terminal]**

> "Now let's write our first fact. Facts in stigmem are immutable entity–relation–value triples with provenance and scope. Here's the anatomy of a fact assertion."

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "local"
  }' | jq '{id, entity, relation, value, hlc, scope}'
```

> "Notice the `value` field — it's a typed object with a `type` key and a `v` key for the payload. The API enforces this format; a bare string like `\"dark mode\"` will be rejected. The node currently supports `string`, `number`, `boolean`, and `json` value types."

> "The response includes an `id` — that's the fact's stable identifier — and an `hlc` timestamp from the node's hybrid logical clock, which is used to order facts across federated nodes."

**[Pause on output, highlight `id` and `hlc`]**

> "Save that `id` — we'll use it in a moment."

---

### [5:30] Query facts back

**[Screen: terminal]**

> "Query the fact we just wrote."

```bash
curl -s 'http://localhost:8765/v1/facts?entity=user:alice&relation=memory:prefers' \
  -H 'X-API-Key: dev-key' | jq '.facts[] | {id, entity, value, scope, timestamp}'
```

> "The query returns a `facts` array. You can filter by `entity`, `relation`, `scope`, or any combination. Pagination is cursor-based."

> "Let's also try a scope filter — only return company-scoped facts."

```bash
curl -s 'http://localhost:8765/v1/facts?entity=user:alice&scope=company' \
  -H 'X-API-Key: dev-key' | jq '.facts'
```

> "Empty — because the fact we wrote was `local` scoped. Scope is enforced strictly."

---

### [6:15] Retract a fact and filter by time

**[Screen: terminal]**

> "To retract a fact, assert the same entity–relation–scope triple with `confidence: 0.0`."

```bash
curl -s -X POST http://localhost:8765/v1/facts \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: dev-key' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 0.0,
    "scope":      "local"
  }' | jq '{id, confidence}'
```

> "Retractions are themselves immutable facts — you can see the full history. Now let's query with a time filter. The `after` parameter accepts an ISO 8601 timestamp and returns only facts newer than that value."

```bash
# ISO timestamp from 5 minutes ago
FIVE_MIN_AGO=$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
              || date -u -v-5M +%Y-%m-%dT%H:%M:%SZ)

curl -s "http://localhost:8765/v1/facts?entity=user:alice&after=${FIVE_MIN_AGO}" \
  -H 'X-API-Key: dev-key' | jq '.facts | length'
```

> "The query parameter is `after` — not `since`. Pass any ISO 8601 value and the node returns facts with timestamps strictly greater than that value."

---

### [7:30] Swagger UI tour

**[Screen: browser, navigate to http://localhost:8765/docs]**

> "The node ships with a full interactive Swagger UI. Every endpoint is here — facts, federation, conflicts, the audit log, and the well-known discovery endpoint."

**[Scroll through endpoint list]**

> "You can try any endpoint right from the browser. Click `POST /v1/facts`, hit `Try it out`, paste in a request body, and fire it."

**[Demo: try a GET /v1/facts call in Swagger UI]**

> "The request and response are both shown inline. The OpenAPI schema is also available at `/openapi.json` — our docs site auto-generates the API reference from it."

---

### [8:30] Teardown

**[Screen: terminal]**

> "To stop the containers and keep your data volumes:"

```bash
make down
```

> "Or to stop and delete all data:"

```bash
docker compose down -v
```

> "The `-v` flag removes the named volumes — use this when you want a clean slate."

---

### [9:00] What's next

**[Screen: docs site or terminal]**

> "That's the basics of running a self-hosted stigmem node. From here:"

> "Watch the federation video to connect two nodes and share facts across them. Watch the MCP adapter video to wire stigmem into Claude Code or any MCP-aware agent."

> "The full docs at stigmem.dev cover asserting facts, scope semantics, the conflict API, Kubernetes deployment with Helm, and more."

> "Thanks for watching."

---

*End of Script 1*
