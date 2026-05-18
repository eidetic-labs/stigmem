---
id: federation
title: Federation
sidebar_label: Federation
audience: Integrator
---

# Federation

**Audience:** Node operators connecting multiple Stigmem nodes.

## Overview

Federation lets two Stigmem nodes exchange facts within agreed scopes. Each node maintains
a local fact store; the federation protocol propagates facts bidirectionally so every
peer eventually holds the same view of each allowed scope.

High-level flow:

1. Node A registers with Node B (`POST /v1/federation/peers`) with an Ed25519 declaration signature
2. Node B verifies the signature against Node A's `/.well-known/stigmem` public key
3. Node B issues a scoped peer token to Node A
4. Node A's background pull loop periodically fetches new facts from Node B using that token
5. The same flow runs in reverse so both nodes replicate to each other

The full protocol is defined in spec §6.

---

## Ed25519 key generation {#key-generation}

Each node needs an Ed25519 keypair. The `infra/soak/keys.py` helper generates and prints
base64url-encoded keys without padding:

```bash
pip install cryptography
python infra/soak/keys.py
# NODE_A_PUBKEY=<base64url-pub>
# NODE_A_PRIVKEY=<base64url-priv>
```

For a single node:

```python
import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

priv = Ed25519PrivateKey.generate()
pub  = priv.public_key()

priv_b64 = base64.urlsafe_b64encode(
    priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
).decode().rstrip("=")

pub_b64 = base64.urlsafe_b64encode(
    pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
).decode().rstrip("=")

print(f"STIGMEM_FEDERATION_PUBKEY={pub_b64}")
print(f"STIGMEM_FEDERATION_PRIVKEY={priv_b64}")
```

**Never store the private key in source control.** Use a Kubernetes Secret or an environment-specific
secrets manager; see [Kubernetes install](../../learn/quickstart/quickstart-tutorial#kubernetes-install-helm) for a
`secretRef` example.

Provide the keys via environment variables before starting the node:

```bash
export STIGMEM_FEDERATION_PUBKEY=<base64url-pub>
export STIGMEM_FEDERATION_PRIVKEY=<base64url-priv>
```

---

## PeerDeclaration and signing (spec §6.1) {#peer-declaration}

To register Node A with Node B, Node A must produce a signed `PeerDeclaration` — a canonical
JSON document that Node B verifies against Node A's published public key.

### Declaration structure

```json
{
  "node_id":            "stigmem:node:node-a",
  "node_url":           "https://stigmem.example.com",
  "federation_pubkey":  "<base64url-encoded Ed25519 pubkey>",
  "allowed_scopes":     ["company", "public"],
  "signed_at":          "2026-05-03T14:00:00Z"
}
```

All fields are required. `node_id` must match the `node_id` reported by `/.well-known/stigmem`.

### Signing

Produce the declaration signature by signing the **canonical JSON** (keys sorted
alphabetically, no extra whitespace) of the declaration object:

```python
import json, base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

# Load the private key
priv_bytes = base64.urlsafe_b64decode(priv_b64 + "==")
priv = Ed25519PrivateKey.from_private_bytes(priv_bytes)

declaration = {
    "node_id":           "stigmem:node:node-a",
    "node_url":          "https://stigmem.example.com",
    "federation_pubkey": pub_b64,
    "allowed_scopes":    ["company", "public"],
    "signed_at":         "2026-05-03T14:00:00Z",
}
# Canonical JSON: sorted keys, no extra whitespace
canonical = json.dumps(declaration, sort_keys=True, separators=(",", ":")).encode()
sig = priv.sign(canonical)
declaration_sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")
```

The `declaration_sig` field is sent alongside the declaration body in the registration request.

### Registration

```bash
curl -X POST https://node-b.example.com/v1/federation/peers \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <nodeB-key>' \
  -d '{
    "node_id":          "stigmem:node:node-a",
    "node_url":         "https://node-a.example.com",
    "allowed_scopes":   ["company", "public"],
    "declaration_sig":  "<base64url-sig>"
  }'
```

A `200 OK` response contains the new peer record with `"status": "active"`. HTTP `409` means
Node A is already registered — safe to skip. HTTP `403` means the signature did not verify.

---

## Peer tokens (spec §6.3) {#peer-tokens}

After registration, Node B issues a **peer token** to Node A. The token is scoped to the
`allowed_scopes` declared at registration and is used exclusively for the pull-replication
endpoint (`GET /v1/federation/facts`).

The token is returned in the registration response:

```json
{
  "peer_token": "<opaque-token>",
  "status":     "active",
  "node_id":    "stigmem:node:node-a",
  "allowed_scopes": ["company", "public"]
}
```

Node A's pull loop stores this token and presents it on every pull request:

```bash
GET /v1/federation/facts?scope=company&cursor=<hlc-cursor>&limit=100
Authorization: Bearer <peer-token>
```

**Peer tokens are not user API keys.** They grant read access only to the declared scopes
and carry no write permissions. If a token is compromised, delete the peer with
`DELETE /v1/federation/peers/<node_id>` and re-register.

---

## Scope enforcement (spec §6.4) {#scope-enforcement}

Scopes control which facts flow across the federation link. Only facts whose `scope` field
matches one of the `allowed_scopes` in the peer registration are replicated.

| Scope | Intended use | Replicated to |
|-------|-------------|---------------|
| `public` | Cross-org knowledge, protocol docs | All federated nodes |
| `company` | Internal agent state, board preferences | Nodes in the same company |
| `team` | Team-level agreements | Nodes sharing the same team scope |
| `local` | Agent working memory, scratch facts | Never replicated |

Facts with `scope=local` are **never** sent to a peer, regardless of `allowed_scopes`.

**Security invariant:** A node may only push or pull facts in scopes it was explicitly
granted at registration time. Attempting to pull `company`-scoped facts with a peer token
registered for `public` only returns an empty result — not an error — so the scope
boundary does not leak existence information.

---

## Conflict detection during ingest (spec §6.5) {#conflict-detection}

When a pulled fact conflicts with a locally-held fact (same entity, relation, and scope but
a different value), the ingest layer records a `ConflictRecord` and surfaces the contradiction.

**Reserved-namespace exemption:** Facts whose entity or relation starts with `stigmem:`
(e.g., `stigmem:conflict:status`, `stigmem:resolves`) are exempt — they carry protocol
state, not semantic content, so differing values represent a state transition. Facts with a
`stigmem://` URI entity (user content) are still subject to contradiction detection.

Resolve conflicts via the Conflicts API or the `resolve_contradiction` MCP tool:

```bash
# List unresolved conflicts
GET /v1/conflicts

# Resolve: keep the winning fact
POST /v1/conflicts/<conflict_id>/resolve
{
  "winning_fact_id": "<fact-id>",
  "resolution_note": "Remote assertion supersedes local draft"
}
```

---

## Cursor-based resume after restart or partition {#soak-results}

The pull loop persists cursor positions in the `replication_cursors` table across both
process restarts and network interruptions.

**Verified behavior (4-node soak, 2026-05-02):**

- `TestCursorResume::test_node_restart_resumes_without_gaps` — 5 public facts asserted on
  a peer while the local node was stopped; on restart with the same SQLite DB, all 5 facts
  were recovered within 30 s via cursor-resume pull. No manual intervention required.
- `TestPartialFailure::test_partial_ingest_then_resume` — 20-fact partial-crash scenario;
  correct cursor position and zero duplicates after resume.
- Idempotent ingest: re-delivered facts (same fact ID) are silently discarded — no
  duplicates even if the pull window overlaps the pre-crash window.

```bash
# Watch cursor behavior in node logs
stigmem node logs --follow | grep "pull from"

# Healthy cursor resume
INFO  pull from stigmem://node-b: cursor=1725349500000.005, got 12 facts, has_more=false

# Full re-pull after cursor loss
INFO  pull from stigmem://node-b: cursor=None, got 100 facts, has_more=true
```

If a node loses its `replication_cursors` table (DB loss/corruption), see the
[DB-loss recovery guide](../../operate/runbooks/cursor-reset-recovery) for the `cursor-export` / `cursor-import`
procedure that bounds re-pull cost.

---

## Monitoring the federation audit log {#audit-log}

Every pull event, peer registration, and conflict detection is written to the federation
audit log:

```bash
# Tail recent audit events
curl -s http://localhost:8765/v1/federation/audit | jq '.entries[-10:]'

# Filter by event type (pull, peer_registered, conflict_detected)
curl -s 'http://localhost:8765/v1/federation/audit?event_type=conflict_detected' | jq '.'
```

Each entry includes `event_type`, `peer_node_id`, `fact_count`, `cursor`, `timestamp`, and
optionally `conflict_id` for conflict events.

Healthy replication looks like a steady stream of `pull` entries with monotonically
increasing cursors. A gap (cursor stuck, `fact_count=0` for many cycles) usually indicates
a network partition or an expired peer token.

---

## Configuration reference {#configuration}

| Variable | Default | Purpose |
|----------|---------|---------|
| `STIGMEM_FEDERATION_PUBKEY` | — | Base64url Ed25519 public key (required for federation) |
| `STIGMEM_FEDERATION_PRIVKEY` | — | Base64url Ed25519 private key (required for federation) |
| `STIGMEM_FEDERATION_PULL_INTERVAL_S` | `30` | How often (seconds) to pull from each peer |
| `STIGMEM_FEDERATION_MAX_PEERS` | `32` | Maximum number of registered peers |
| `STIGMEM_FEDERATION_PULL_LIMIT` | `100` | Maximum facts per pull request |
| `STIGMEM_FEDERATION_PUSH_ENABLED` | `false` | Enable outbound push in addition to pull |

Lower `STIGMEM_FEDERATION_PULL_INTERVAL_S` in dev environments for faster replication during
testing. In production, 30 s is a reasonable default for agent-state facts; increase it for
nodes with high write rates to avoid thundering-herd pull storms.

---

## Security hardening {#security}

- **Key rotation:** Rotate federation keypairs by registering the new key on all peers, then
  replacing the environment variables and restarting. Peers verify signatures against the
  current `/.well-known/stigmem` public key on each registration request — old keys are not
  cached.
- **Scope minimization:** Register peers with only the scopes they need. A read-only analytics
  node should be granted `public` only, not `company`.
- **Revocation:** To remove a peer, `DELETE /v1/federation/peers/<node_id>`. The peer's pull
  requests will receive `401` until it re-registers.
- **TLS:** In production, always terminate TLS at the ingress layer. The pull endpoint transmits
  fact values; without TLS, peer tokens and fact payloads are visible on the wire.

---

## External integrator onboarding {#external-onboarding}

This section is for teams running a Stigmem node who want to federate with an existing
deployment — for example, a partner network node that speaks the Stigmem federation protocol.

:::tip OpenClaw users — use the ClawHub skill

If you are integrating Stigmem into an **OpenClaw** agent, the fastest path is the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node). It handles
the boot handshake, handoff, decision, and escalation surfaces in a single install and
bundles the adapter so no separate package setup is required.

```bash
skill install stigmem-node
```

Set `STIGMEM_URL` (and optionally `STIGMEM_API_KEY`) and the skill is ready to use.
Full usage docs and the security model are in the
[`adapters/openclaw` README](https://github.com/eidetic-labs/stigmem/tree/main/adapters/openclaw#readme).

:::



### Prerequisites

- Stigmem node v1.0+ running at a stable, publicly reachable URL.
- `STIGMEM_FEDERATION_PUBKEY` and `STIGMEM_FEDERATION_PRIVKEY` set (or let the node auto-generate on first start).
- `STIGMEM_NODE_URL` set to your node's public URL (used in well-known discovery and peer registration).
- Federation enabled: `STIGMEM_FEDERATION_ENABLED=true`.

### Integration checklist

1. **Share your well-known URL** (`GET <your-node-url>/.well-known/stigmem`) with the partner operator so they can retrieve your `node_id` and `federation_pubkey`.

2. **Agree on scopes.** Start with `["public"]`. Expanding to `company` or `team` requires explicit operator opt-in and a re-registration with the updated `allowed_scopes`.

3. **Generate a declaration signature.** See [PeerDeclaration and signing](#peer-declaration) above.

4. **Register your node with the partner** via `POST /v1/federation/peers` on their node, including the signed declaration.

5. **Ask the partner to register with your node** in return (bidirectional peering; both sides pull from each other).

6. **Confirm peer activation** on both sides:
   ```bash
   curl http://your-node:8765/v1/federation/peers | jq '.[].status'
   # → "active"
   ```

7. **Smoke test** — assert one `public`-scoped fact on each node and verify it appears on the other within two pull intervals (≤ 60 s at default settings):
   ```bash
   # On your node
   curl -X POST http://your-node:8765/v1/facts \
     -H 'Authorization: Bearer <api-key>' \
     -H 'Content-Type: application/json' \
     -d '{"entity":"test:ping","relation":"test:status","value":"hello","scope":"public"}'

   # On partner node (after ≤60 s)
   curl 'http://partner-node:8765/v1/facts?entity=test:ping' \
     -H 'Authorization: Bearer <partner-api-key>' | jq '.facts[].value'
   # → "hello"
   ```

8. **Monitor the audit log** on both nodes for any `rejected_token`, `scope_violation`, or `replay_attempt` events during the first hour.

### Test node for integration validation

To validate the integration before pointing at a production node, run a local test instance
using Docker:

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_FEDERATION_ENABLED=true \
  -e STIGMEM_NODE_URL=http://host.docker.internal:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

Or with Docker Compose (two nodes, bidirectional peering wired automatically):

```bash
docker compose -f infra/docker-compose.yml up
# node-a: http://localhost:8765
# node-b: http://localhost:8766
```

Peer registrations are seeded by `infra/soak/setup_peers.py`. See the
[4-node topology guide](./federation-4node) for the full soak environment.

### Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Peer stays `pending_verification` | Your node's well-known endpoint not reachable from partner | Check `STIGMEM_NODE_URL` and firewall/NAT rules |
| `rejected_token` in partner audit log | Token expired or `sub` mismatch | Confirm both nodes serve the correct `node_id` |
| No facts flowing after activation | Scope mismatch | Re-register with matching `allowed_scopes` on both sides |
| `scope_violation` audit events | Pull asked for a scope beyond what was declared | Update and re-submit the peer registration |

---

## See also

- [Quickstart — two nodes federating](../../learn/quickstart/quickstart-tutorial) — local two-node test in under 5 minutes
- [Paperclip connector](../connectors/paperclip) — deploying stigmem as a Paperclip agent fleet's persistent fact store
- [4-node topology](./federation-4node) — full-mesh setup, failure injection, soak metrics
- [Federation API Reference](../../reference/api) — full endpoint reference
- [Architecture](../../reference/architecture) — HLC, PeerDeclaration internals, spec §6
