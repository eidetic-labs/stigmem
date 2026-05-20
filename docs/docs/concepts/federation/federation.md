---
title: Federation
sidebar_label: Federation
audience: Integrator
---

# Federation

<p className="stigmem-meta"><span>8 min read</span><span>Node operator</span><span>Spec-05-Federation-Trust</span></p>

<div className="stigmem-lead">

**What this page is**

Operator guide for connecting two Stigmem nodes. Federation lets
nodes exchange facts within agreed scopes; each node maintains a
local fact store, and the protocol propagates facts bidirectionally
so every peer eventually holds the same view of each allowed scope.

</div>

## Overview

High-level flow:

<ol className="stigmem-steps">
<li>Node A registers with Node B (<code>POST /v1/federation/peers</code>) with an Ed25519 declaration signature.</li>
<li>Node B verifies the signature against Node A's <code>/.well-known/stigmem</code> public key.</li>
<li>Node B issues a scoped peer token to Node A.</li>
<li>Node A's background pull loop periodically fetches new facts from Node B using that token.</li>
<li>The same flow runs in reverse so both nodes replicate to each other.</li>
</ol>

The full protocol is defined in Spec-05-Federation-Trust.

## Ed25519 key generation \{#key-generation\}

Each node needs an Ed25519 keypair. The `infra/soak/keys.py` helper
generates and prints base64url-encoded keys without padding:

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

<div className="stigmem-keypoint">

**Never store the private key in source control.**

Use an environment-specific secrets manager (Docker secrets, AWS
Secrets Manager, Vault, Doppler, etc.). The Helm chart and its
<code>secretRef</code> example are deferred to
[<code>experimental/deploy-helm/</code>](https://github.com/eidetic-labs/stigmem/tree/main/experimental/deploy-helm)
in v0.9.0a1.

</div>

Provide the keys via environment variables before starting the node:

```bash
export STIGMEM_FEDERATION_PUBKEY=<base64url-pub>
export STIGMEM_FEDERATION_PRIVKEY=<base64url-priv>
```

## PeerDeclaration and signing \{#peer-declaration\}

To register Node A with Node B, Node A must produce a signed
`PeerDeclaration` — a canonical JSON document that Node B verifies
against Node A's published public key.

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

All fields are required. `node_id` must match the `node_id` reported
by `/.well-known/stigmem`.

### Signing

Produce the declaration signature by signing the **canonical JSON**
(keys sorted alphabetically, no extra whitespace) of the declaration
object:

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

The `declaration_sig` field is sent alongside the declaration body in
the registration request.

### Registration

```bash
curl -X POST https://node-b.example.com/v1/federation/peers \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <nodeB-key>' \
  -d '{
    "node_id":          "stigmem:node:node-a",
    "node_url":         "https://node-a.example.com",
    "allowed_scopes":   ["company", "public"],
    "declaration_sig":  "<base64url-sig>"
  }'
```

<div className="stigmem-fields">

<div>
<dt>Response</dt>
<dt><span className="stigmem-fields__type">Meaning</span></dt>
<dd>What to do</dd>
</div>

<div>
<dt><code>200 OK</code></dt>
<dt><span className="stigmem-fields__type">success</span></dt>
<dd>Contains the new peer record with <code>"status": "active"</code>.</dd>
</div>

<div>
<dt><code>409 Conflict</code></dt>
<dt><span className="stigmem-fields__type">already registered</span></dt>
<dd>Node A is already registered — safe to skip.</dd>
</div>

<div>
<dt><code>403 Forbidden</code></dt>
<dt><span className="stigmem-fields__type">signature failure</span></dt>
<dd>The signature did not verify.</dd>
</div>

</div>

## Peer tokens \{#peer-tokens\}

After registration, Node B issues a **peer token** to Node A. The
token is scoped to the `allowed_scopes` declared at registration and
is used exclusively for the pull-replication endpoint
(`GET /v1/federation/facts`).

The token is returned in the registration response:

```json
{
  "peer_token": "<opaque-token>",
  "status":     "active",
  "node_id":    "stigmem:node:node-a",
  "allowed_scopes": ["company", "public"]
}
```

Node A's pull loop stores this token and presents it on every pull
request:

```bash
GET /v1/federation/facts?scope=company&cursor=<hlc-cursor>&limit=100
Authorization: Bearer <peer-token>
```

<div className="stigmem-keypoint">

**Peer tokens are not user API keys.**

They grant read access only to the declared scopes and carry no
write permissions. If a token is compromised, delete the peer with
<code>DELETE /v1/federation/peers/&lt;node_id&gt;</code> and
re-register.

</div>

## Scope enforcement \{#scope-enforcement\}

Scopes control which facts flow across the federation link. Only
facts whose `scope` field matches one of the `allowed_scopes` in the
peer registration are replicated.

<div className="stigmem-fields">

<div>
<dt>Scope</dt>
<dt><span className="stigmem-fields__type">Intended use</span></dt>
<dd>Replicated to</dd>
</div>

<div>
<dt><code>public</code></dt>
<dt><span className="stigmem-fields__type">cross-org knowledge</span></dt>
<dd>All federated nodes.</dd>
</div>

<div>
<dt><code>company</code></dt>
<dt><span className="stigmem-fields__type">internal agent state</span></dt>
<dd>Nodes in the same company.</dd>
</div>

<div>
<dt><code>team</code></dt>
<dt><span className="stigmem-fields__type">team-level agreements</span></dt>
<dd>Nodes sharing the same team scope.</dd>
</div>

<div>
<dt><code>local</code></dt>
<dt><span className="stigmem-fields__type">agent working memory</span></dt>
<dd>Never replicated.</dd>
</div>

</div>

Facts with `scope=local` are **never** sent to a peer, regardless of
`allowed_scopes`.

<div className="stigmem-keypoint">

**Security invariant.**

A node may only push or pull facts in scopes it was explicitly
granted at registration time. Attempting to pull <code>company</code>-scoped
facts with a peer token registered for <code>public</code> only
returns an empty result — not an error — so the scope boundary does
not leak existence information.

</div>

## Conflict detection during ingest \{#conflict-detection\}

When a pulled fact conflicts with a locally-held fact (same entity,
relation, and scope but a different value), the ingest layer records
a `ConflictRecord` and surfaces the contradiction.

<div className="stigmem-keypoint">

**Reserved-namespace exemption.**

Facts whose entity or relation starts with <code>stigmem:</code>
(e.g., <code>stigmem:conflict:status</code>, <code>stigmem:resolves</code>)
are exempt — they carry protocol state, not semantic content. Facts
with a <code>stigmem://</code> URI entity (user content) are still
subject to contradiction detection.

</div>

Resolve conflicts via the Conflicts API or the
`resolve_contradiction` MCP tool:

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

## Cursor-based resume after restart or partition \{#soak-results\}

The pull loop persists cursor positions in the `replication_cursors`
table across both process restarts and network interruptions.

**Verified behavior (4-node soak, 2026-05-02):**

<div className="stigmem-grid">

<div><h4>Restart resume without gaps</h4><p><code>TestCursorResume::test_node_restart_resumes_without_gaps</code> — 5 public facts asserted on a peer while the local node was stopped; on restart with the same SQLite DB, all 5 facts were recovered within 30s via cursor-resume pull. No manual intervention required.</p></div>
<div><h4>Partial ingest resume</h4><p><code>TestPartialFailure::test_partial_ingest_then_resume</code> — 20-fact partial-crash scenario; correct cursor position and zero duplicates after resume.</p></div>
<div><h4>Idempotent ingest</h4><p>Re-delivered facts (same fact ID) are silently discarded — no duplicates even if the pull window overlaps the pre-crash window.</p></div>

</div>

```bash
# Watch cursor behavior in node logs
stigmem node logs --follow | grep "pull from"

# Healthy cursor resume
INFO  pull from stigmem://node-b: cursor=1725349500000.005, got 12 facts, has_more=false

# Full re-pull after cursor loss
INFO  pull from stigmem://node-b: cursor=None, got 100 facts, has_more=true
```

If a node loses its `replication_cursors` table (DB loss/corruption),
see the [DB-loss recovery guide](../../operators/runbooks/cursor-reset-recovery)
for the `cursor-export` / `cursor-import` procedure that bounds
re-pull cost.

## Monitoring the federation audit log \{#audit-log\}

Every pull event, peer registration, and conflict detection is
written to the federation audit log:

```bash
# Tail recent audit events
curl -s http://localhost:8765/v1/federation/audit | jq '.entries[-10:]'

# Filter by event type (pull, peer_registered, conflict_detected)
curl -s 'http://localhost:8765/v1/federation/audit?event_type=conflict_detected' | jq '.'
```

Each entry includes `event_type`, `peer_node_id`, `fact_count`,
`cursor`, `timestamp`, and optionally `conflict_id` for conflict
events.

Healthy replication looks like a steady stream of `pull` entries with
monotonically increasing cursors. A gap (cursor stuck,
`fact_count=0` for many cycles) usually indicates a network partition
or an expired peer token.

## Configuration reference \{#configuration\}

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PUBKEY</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Base64url Ed25519 public key.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PRIVKEY</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Base64url Ed25519 private key.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code></dt>
<dt><span className="stigmem-fields__type"><code>30</code></span></dt>
<dd>How often (seconds) to pull from each peer.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_MAX_PEERS</code></dt>
<dt><span className="stigmem-fields__type"><code>32</code></span></dt>
<dd>Maximum number of registered peers.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_LIMIT</code></dt>
<dt><span className="stigmem-fields__type"><code>100</code></span></dt>
<dd>Maximum facts per pull request.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PUSH_ENABLED</code></dt>
<dt><span className="stigmem-fields__type"><code>false</code></span></dt>
<dd>Enable outbound push in addition to pull.</dd>
</div>

</div>

Lower `STIGMEM_FEDERATION_PULL_INTERVAL_S` in dev environments for
faster replication during testing. In production, 30s is a reasonable
default for agent-state facts; increase it for nodes with high write
rates to avoid thundering-herd pull storms.

## Security hardening \{#security\}

<div className="stigmem-grid">

<div><h4>Key rotation</h4><p>Rotate federation keypairs by registering the new key on all peers, then replacing the environment variables and restarting. Peers verify signatures against the current <code>/.well-known/stigmem</code> public key on each registration request — old keys are not cached.</p></div>
<div><h4>Scope minimization</h4><p>Register peers with only the scopes they need. A read-only analytics node should be granted <code>public</code> only, not <code>company</code>.</p></div>
<div><h4>Revocation</h4><p>To remove a peer, <code>DELETE /v1/federation/peers/&lt;node_id&gt;</code>. The peer's pull requests will receive <code>401</code> until it re-registers.</p></div>
<div><h4>TLS</h4><p>In production, always terminate TLS at the ingress layer. The pull endpoint transmits fact values; without TLS, peer tokens and fact payloads are visible on the wire.</p></div>

</div>

## External integrator onboarding \{#external-onboarding\}

This section is for teams running a Stigmem node who want to
federate with an existing deployment — for example, a partner
network node that speaks the Stigmem federation protocol.

:::caution OpenClaw users — alpha connector only

If you are integrating Stigmem into an **OpenClaw** agent, the
fastest path is the
[`stigmem-node` ClawHub skill](https://clawhub.ai/skills/stigmem-node).
It handles the boot handshake, handoff, decision, and escalation
surfaces in a single install and bundles the adapter so no separate
package setup is required.

```bash
skill install stigmem-node
```

This path is for alpha evaluation only, not production federation.
Use a private node and a least-privilege key, and read the open
audit limitations before using the adapter in an agent workflow.
Full usage docs and the security model are in the
[`adapters/openclaw` README](https://github.com/eidetic-labs/stigmem/tree/main/adapters/openclaw#readme);
the current adopter warning is in
[LIMITATIONS.md Spec-16-Namespace-Registry](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md#9-running-the-openclaw-bundled-adapter-as-is).

:::

### Prerequisites

<div className="stigmem-grid">

<div><h4>Stigmem node v1.0+ running</h4><p>At a stable, publicly reachable URL.</p></div>
<div><h4>Federation keys set</h4><p><code>STIGMEM_FEDERATION_PUBKEY</code> and <code>STIGMEM_FEDERATION_PRIVKEY</code> (or let the node auto-generate on first start).</p></div>
<div><h4><code>STIGMEM_NODE_URL</code> set</h4><p>To your node's public URL (used in well-known discovery and peer registration).</p></div>
<div><h4>Federation enabled</h4><p><code>STIGMEM_FEDERATION_ENABLED=true</code>.</p></div>

</div>

### Integration checklist

<ol className="stigmem-steps">
<li><strong>Share your well-known URL</strong> (<code>GET &lt;your-node-url&gt;/.well-known/stigmem</code>) with the partner operator so they can retrieve your <code>node_id</code> and <code>federation_pubkey</code>.</li>
<li><strong>Agree on scopes.</strong> Start with <code>["public"]</code>. Expanding to <code>company</code> or <code>team</code> requires explicit operator opt-in and a re-registration with the updated <code>allowed_scopes</code>.</li>
<li><strong>Generate a declaration signature.</strong> See <a href="#peer-declaration">PeerDeclaration and signing</a> above.</li>
<li><strong>Register your node with the partner</strong> via <code>POST /v1/federation/peers</code> on their node, including the signed declaration.</li>
<li><strong>Ask the partner to register with your node</strong> in return (bidirectional peering; both sides pull from each other).</li>
<li><strong>Confirm peer activation</strong> on both sides with <code>curl http://your-node:8765/v1/federation/peers | jq '.[].status'</code>.</li>
<li><strong>Smoke test.</strong> Assert one <code>public</code>-scoped fact on each node and verify it appears on the other within two pull intervals (≤ 60s at default settings).</li>
<li><strong>Monitor the audit log</strong> on both nodes for any <code>rejected_token</code>, <code>scope_violation</code>, or <code>replay_attempt</code> events during the first hour.</li>
</ol>

```bash
# On your node
curl -X POST http://your-node:8765/v1/facts \
  -H 'Authorization: Bearer <api-key>' \
  -H 'Content-Type: application/json' \
  -d '{"entity":"test:ping","relation":"test:status","value":"hello","scope":"public"}'

# On partner node (after ≤60s)
curl 'http://partner-node:8765/v1/facts?entity=test:ping' \
  -H 'Authorization: Bearer <partner-api-key>' | jq '.facts[].value'
# → "hello"
```

### Test node for integration validation

To validate the integration before pointing at a production node, run
a local test instance using Docker. The snippet below pulls `:latest`
for quick experimentation; for production federation use a pinned
version tag (`:0.9.0a1`) or a digest pin — see the
[tag-selection guide](../../operators/deployment/install#image-tags).

```bash
docker run --rm -p 8765:8765 \
  -e STIGMEM_FEDERATION_ENABLED=true \
  -e STIGMEM_NODE_URL=http://host.docker.internal:8765 \
  ghcr.io/eidetic-labs/stigmem-node:latest
```

Or with Docker Compose (two nodes, bidirectional peering wired
automatically):

```bash
docker compose -f infra/docker-compose.yml up
# node-a: http://localhost:8765
# node-b: http://localhost:8766
```

Peer registrations are seeded by `infra/soak/setup_peers.py`. See
the [4-node topology guide](./federation-4node) for the full soak
environment.

### Troubleshooting

<div className="stigmem-fields">

<div>
<dt>Symptom</dt>
<dt><span className="stigmem-fields__type">Likely cause</span></dt>
<dd>Fix</dd>
</div>

<div>
<dt>Peer stays <code>pending_verification</code></dt>
<dt><span className="stigmem-fields__type">well-known not reachable</span></dt>
<dd>Check <code>STIGMEM_NODE_URL</code> and firewall/NAT rules.</dd>
</div>

<div>
<dt><code>rejected_token</code> in partner audit log</dt>
<dt><span className="stigmem-fields__type">token expired or <code>sub</code> mismatch</span></dt>
<dd>Confirm both nodes serve the correct <code>node_id</code>.</dd>
</div>

<div>
<dt>No facts flowing after activation</dt>
<dt><span className="stigmem-fields__type">scope mismatch</span></dt>
<dd>Re-register with matching <code>allowed_scopes</code> on both sides.</dd>
</div>

<div>
<dt><code>scope_violation</code> audit events</dt>
<dt><span className="stigmem-fields__type">pull beyond declared scope</span></dt>
<dd>Update and re-submit the peer registration.</dd>
</div>

</div>

## See also

<div className="stigmem-next">

<a href="../../get-started/quickstart-tutorial">
<strong>Get started</strong>
<span>Two-node quickstart</span>
<small>Local two-node test in under 5 minutes.</small>
</a>

<a href="https://github.com/eidetic-labs/stigmem/tree/main/experimental/adapter-paperclip">
<strong>Experimental</strong>
<span>Paperclip connector</span>
<small>Deploying stigmem as a Paperclip agent fleet's persistent fact store.</small>
</a>

<a href="./federation-4node">
<strong>Concepts</strong>
<span>4-node topology</span>
<small>Full-mesh setup, failure injection, soak metrics.</small>
</a>

<a href="../../reference/api">
<strong>Reference</strong>
<span>Federation API</span>
<small>Full endpoint reference.</small>
</a>

</div>
