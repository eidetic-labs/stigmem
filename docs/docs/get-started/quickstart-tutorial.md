---
title: Quickstart — two nodes federating
sidebar_label: Federation Tutorial
slug: quickstart-tutorial
---

# Quickstart — two nodes federating

<p className="stigmem-meta"><span>5 min hands-on</span><span>For first-time operators</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll do**

Run two Stigmem nodes on one machine and watch a fact asserted on
Node A replicate automatically to Node B. End-to-end smoke test
including peer handshake, replication, and audit log inspection.

</div>

<div className="stigmem-keypoint">

**The fastest path is `make demo`.**

It starts two local nodes, registers them as peers, asserts a fact on
node A, waits for pull replication, checks node B, prints recent
audit entries, and tears the stack down. Everything below explains
what `make demo` does and how to drive it manually.

</div>

## Prerequisites

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Version</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Docker</dt>
<dt><span className="stigmem-fields__type">≥ 24</span></dt>
<dd>Required.</dd>
</div>

<div>
<dt>Docker Compose (v2)</dt>
<dt><span className="stigmem-fields__type">≥ 2.20</span></dt>
<dd>Required.</dd>
</div>

<div>
<dt><code>curl</code> + <code>jq</code></dt>
<dt><span className="stigmem-fields__type">any recent</span></dt>
<dd>For inspecting JSON responses.</dd>
</div>

<div>
<dt><code>helm</code></dt>
<dt><span className="stigmem-fields__type">≥ 3.14</span></dt>
<dd>Kubernetes install only — Helm chart is deferred in v0.9.0a2 (see caution below).</dd>
</div>

</div>

No Python installation required — the nodes run in containers.

## Step 1 — Clone and start the stack

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
make demo
```

`make demo` runs `scripts/quickstart-verify.sh`. By default it uses
the pinned GHCR image from `docker-compose.yml` for speed.
Contributors who need to prove the local working tree can set
`DEMO_BUILD=1 make demo` to force a local image build first.

The quickstart starts two services:

<div className="stigmem-fields">

<div>
<dt>Service</dt>
<dt><span className="stigmem-fields__type">Host port</span></dt>
<dd>Role</dd>
</div>

<div>
<dt><code>node-a</code></dt>
<dt><span className="stigmem-fields__type">8765</span></dt>
<dd>First Stigmem node.</dd>
</div>

<div>
<dt><code>node-b</code></dt>
<dt><span className="stigmem-fields__type">8766</span></dt>
<dd>Second Stigmem node — the federation peer.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Local-dev defaults.**

The compose file sets <code>STIGMEM_FEDERATION_INSECURE=1</code> plus
<code>STIGMEM_LOCAL_DEV_ALLOW_INSECURE_NON_LOOPBACK=1</code> because
containers address each other with Docker service DNS names instead
of <code>localhost</code>. Do not carry those flags into production —
use mTLS for any deployed federation.

</div>

If ports 8765 / 8766 are busy, the demo script automatically selects
free host ports starting at 18765.

## Troubleshooting `make demo`

### Ports 8765/8766 are already in use

The containers still listen on port 8765 internally, but the host
ports can move. When 8765 or 8766 are busy, `make demo` automatically
selects available host ports starting at 18765 and prints the Node A
and Node B URLs it used.

Use those printed URLs for manual `curl` commands, or set explicit
ports before running the demo:

```bash
STIGMEM_NODE_A_HOST_PORT=18765 STIGMEM_NODE_B_HOST_PORT=18766 make demo
```

If a browser or `curl` command still points at `localhost:8765` or
`localhost:8766`, it may be talking to another local process instead
of the demo stack.

### Docker image pull failures

By default, the demo pulls the pinned GHCR image from
`docker-compose.yml`. Transient network, registry, or local Docker
cache failures are usually safe to retry. Contributors validating
local changes — or anyone blocked by a published image pull — can
build the local image instead:

```bash
DEMO_BUILD=1 make demo
```

### Failure before teardown

`make demo` prints each step before it runs it. When a failure happens
before teardown, the first failing step and the Docker error output
are the most useful diagnostics.

To keep containers available for inspection, rerun with:

```bash
KEEP_UP=1 make demo
```

Then inspect the stack with:

```bash
docker compose ps
docker compose logs node-a node-b
```

When you are done, clean up with
`docker compose down -v --remove-orphans`.

## Step 2 — Verify federation

The demo prints each step as it runs:

```text
Step 0 — docker compose up -d
Step 2 — Inspecting /.well-known/stigmem
Step 3 — Peer handshake (both directions)
Step 4 — Asserting fact on node-a
Step 5 — Waiting 35s for federation pull
Step 6 — Federation audit log on node-b
```

`quickstart smoke test PASSED` confirms three things:

<div className="stigmem-grid">

<div>
<h4>Peer declaration accepted</h4>
<p>The receiving node verified the signed peer declaration.</p>
</div>

<div>
<h4>Pull replication moved the fact</h4>
<p>Node B observed the fact written on Node A within the pull interval.</p>
</div>

<div>
<h4>Audit endpoint readable</h4>
<p>The federation audit log returned the expected pull and peer events.</p>
</div>

</div>

To keep the demo stack running for manual inspection:

```bash
KEEP_UP=1 make demo
```

## Step 3 — Manual fact assertion

With `KEEP_UP=1`, assert another fact on node A:

```bash
curl -s -X POST "${NODE_A:-http://localhost:8765}/v1/facts" \
  -H 'Content-Type: application/json' \
  -d '{
    "entity":     "user:alice",
    "relation":   "memory:prefers",
    "value":      {"type": "string", "v": "dark mode"},
    "source":     "agent:settings",
    "confidence": 1.0,
    "scope":      "company"
  }' | jq '{id, entity, relation, value, scope}'
```

Record the `id` from the response — you'll use it to confirm
replication.

## Step 4 — Verify cross-node replication

Node B pulls facts from Node A on the background pull interval
(default 30 s):

```bash
sleep 35
curl -s "${NODE_B:-http://localhost:8766}/v1/facts?entity=user:alice&scope=company" \
  -H 'Content-Type: application/json' | jq '.facts[] | {id, entity, value, scope, source_node}'
```

The fact asserted on Node A (`localhost:8765`) should appear on Node B
(`localhost:8766`) with a `source_node` field pointing to Node A's
`node_id`.

:::info Pull interval
The default pull interval is 30 s
(`STIGMEM_FEDERATION_PULL_INTERVAL_S`). Lower it in
`docker-compose.yml` for testing.
:::

## Step 5 — Federation audit log

Every pull event and peer action is recorded:

```bash
curl -s "${NODE_B:-http://localhost:8766}/v1/federation/audit" | jq '.entries[-3:]'
```

## Makefile targets

<div className="stigmem-fields">

<div>
<dt>Target</dt>
<dt><span className="stigmem-fields__type">Use for</span></dt>
<dd>What it does</dd>
</div>

<div>
<dt><code>make demo</code></dt>
<dt><span className="stigmem-fields__type">smoke</span></dt>
<dd>End-to-end two-node smoke test: start, peer, assert, replicate, audit, tear down.</dd>
</div>

<div>
<dt><code>DEMO_BUILD=1 make demo</code></dt>
<dt><span className="stigmem-fields__type">contributors</span></dt>
<dd>Same demo, but force-build the local working tree image.</dd>
</div>

<div>
<dt><code>KEEP_UP=1 make demo</code></dt>
<dt><span className="stigmem-fields__type">inspection</span></dt>
<dd>Leave the stack running after the demo for manual inspection.</dd>
</div>

<div>
<dt><code>make demo-attack</code></dt>
<dt><span className="stigmem-fields__type">security</span></dt>
<dd>Malicious-peer rejection demo: unauthorized scope write and source forgery.</dd>
</div>

<div>
<dt><code>DEMO_ATTACK_TRANSCRIPT=/tmp/demo-attack.json make demo-attack</code></dt>
<dt><span className="stigmem-fields__type">audit</span></dt>
<dd>Same malicious-peer demo, plus a small JSON transcript with no secrets or private keys.</dd>
</div>

</div>

For ad hoc compose work, use `docker compose up -d` and
`docker compose down -v`.

## Malicious-Peer Rejection Demo

`make demo-attack` runs the focused malicious-peer acceptance gate
without leaving a demo cluster running. It validates two rejection
paths:

<div className="stigmem-grid">

<div>
<h4>Unauthorized scope write</h4>
<p>A peer attempts to write into a scope outside its allowed scopes.</p>
</div>

<div>
<h4>Source-forged public write</h4>
<p>A peer claims another source identity when writing a <code>public</code>-scope fact.</p>
</div>

</div>

Expected result:

<div className="stigmem-grid">

<div>
<h4>Exit success</h4>
<p>The command exits successfully.</p>
</div>

<div>
<h4>Focused gate passed</h4>
<p>Output shows the focused pytest gate passed.</p>
</div>

<div>
<h4>Rejection recorded</h4>
<p>The rejected attempts are recorded as rejection / audit outcomes — not accepted replicated facts.</p>
</div>

</div>

To save a machine-readable summary:

```bash
DEMO_ATTACK_TRANSCRIPT=/tmp/demo-attack.json make demo-attack
jq . /tmp/demo-attack.json
```

The transcript records the gate command, exit code, elapsed time, and
expected scenario outcomes. It does not contain secrets or private
keys.

:::caution Helm / Kubernetes is deferred in v0.9.0a4
The Helm chart has been moved to
[`experimental/deploy-helm/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental/deploy-helm)
per
[ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md).
It remains buildable but is unsupported until the
[ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md)
pass. The supported v0.9.0a4 deployment surface is Docker Compose
(above).
:::

:::tip Key generation
Generate Ed25519 keypairs with `python3 infra/soak/keys.py`. Keys must
be base64url-encoded without padding (`=`).
:::

## Peer registration internals

The demo bootstraps local-only admin-federation keys inside each fresh
container, registers each direction by running the CLI, then approves
each pending peer with its public-key fingerprint:

```bash
stigmem federation register-peer \
  --local-url  http://node-a:8765 \
  --remote-url http://node-b:8765 \
  --scopes company,public \
  --api-key "$NODE_B_ADMIN_KEY"
```

The receiving node fetches the sender's `/.well-known/stigmem`,
verifies the federation public key, and stores a pending peer record.
The script approves the peer after matching the SHA-256 fingerprint of
the advertised public key. HTTP 409 means a prior run already
registered that peer; the demo clears volumes before starting so the
handshake is deterministic.

### Environment overrides

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Purpose</dd>
</div>

<div>
<dt><code>STIGMEM_NODE_A_HOST_PORT</code></dt>
<dt><span className="stigmem-fields__type">first free ≥ 18765</span></dt>
<dd>Node A host port for the demo script.</dd>
</div>

<div>
<dt><code>STIGMEM_NODE_B_HOST_PORT</code></dt>
<dt><span className="stigmem-fields__type">next free after node A</span></dt>
<dd>Node B host port for the demo script.</dd>
</div>

<div>
<dt><code>PULL_WAIT_S</code></dt>
<dt><span className="stigmem-fields__type"><code>35</code></span></dt>
<dd>Seconds to wait before checking node B for replicated facts.</dd>
</div>

<div>
<dt><code>KEEP_UP</code></dt>
<dt><span className="stigmem-fields__type"><code>0</code></span></dt>
<dd>Set to <code>1</code> to leave containers running after the demo.</dd>
</div>

<div>
<dt><code>DEMO_BUILD</code></dt>
<dt><span className="stigmem-fields__type"><code>0</code></span></dt>
<dd>Set to <code>1</code> to force <code>docker compose up --build -d</code>.</dd>
</div>

</div>

### Idempotency

<div className="stigmem-keypoint">

**Safe to re-run.**

The script starts by running
<code>docker compose down -v --remove-orphans</code> so stale peer
registrations, test facts, and volumes do not affect the next
handshake.

</div>

## Teardown

```bash
docker compose down -v # stop and delete all data volumes
```

## What's next

<div className="stigmem-next">

<a href="../concepts/facts/asserting-facts">
<strong>Concept</strong>
<span>Asserting facts</span>
<small>Full fact schema, scopes, TTLs.</small>
</a>

<a href="../concepts/federation/">
<strong>Concept</strong>
<span>Federation</span>
<small>Scope enforcement, conflict resolution, production keys.</small>
</a>

<a href="../concepts/federation/federation-4node">
<strong>Concept</strong>
<span>4-node topology</span>
<small>Full-mesh setup, failure injection, soak metrics.</small>
</a>

<a href="../reference/api/">
<strong>Reference</strong>
<span>API reference</span>
<small>Full endpoint reference.</small>
</a>

</div>
