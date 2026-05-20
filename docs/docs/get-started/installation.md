---
title: Installation
sidebar_label: Installation
---

# Installation

<p className="stigmem-meta"><span>5 min read</span><span>For first-time operators</span><span>Updated 2026-05-19</span></p>

<div className="stigmem-lead">

**What you'll do**

Get a local Stigmem node running. Three paths: a two-node federated
quickstart with Docker Compose (fastest), running from the Python
source directly (development), or installing as a persistent macOS
LaunchAgent (always-on local node).

</div>

<div className="stigmem-keypoint">

**Local-dev defaults only.**

The Docker Compose path runs plaintext federation between two
loopback containers for the quickstart. Production federation requires
mTLS — see [mTLS federation transport](../security/mtls.md) before
exposing a node outside of localhost.

</div>

## Prerequisites

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Minimum version</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Docker</dt>
<dt><span className="stigmem-fields__type">≥ 24</span></dt>
<dd>The fastest path — pre-built image and Compose definitions.</dd>
</div>

<div>
<dt>Docker Compose (v2)</dt>
<dt><span className="stigmem-fields__type">≥ 2.20</span></dt>
<dd>Used by the quickstart and the 4-node soak topology.</dd>
</div>

<div>
<dt>Python (alt. path)</dt>
<dt><span className="stigmem-fields__type">≥ 3.11</span></dt>
<dd>Only needed for the source-tree development path or the macOS LaunchAgent.</dd>
</div>

</div>

## Path A · Single-command install (two-node federation)

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
docker compose up --build -d
```

This builds the reference node image once and starts two federated nodes:

| Container | Host port | Well-known URL |
|-----------|-----------|----------------|
| `node-a` | 8765 | `http://localhost:8765/.well-known/stigmem` |
| `node-b` | 8766 | `http://localhost:8766/.well-known/stigmem` |

Verify both are healthy:

```bash
curl -s http://localhost:8765/healthz   # {"status":"ok"}
curl -s http://localhost:8766/healthz   # {"status":"ok"}
```

For the full two-node federation walk-through — peer handshake, fact
assertion, replication verification — continue to the
[Quickstart](./quickstart-tutorial).

## Docker Compose configuration

`docker-compose.yml` in the repo root sets up the two-node quickstart
cluster. Key environment variables:

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ENABLED</code></dt>
<dt><span className="stigmem-fields__type"><code>true</code></span></dt>
<dd>Enable / disable federation pull loop.</dd>
</div>

<div>
<dt><code>STIGMEM_NODE_URL</code></dt>
<dt><span className="stigmem-fields__type">(container URL)</span></dt>
<dd>Public URL of this node — used in PeerDeclarations.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_INSECURE</code></dt>
<dt><span className="stigmem-fields__type"><code>1</code></span></dt>
<dd>Local quickstart-only plaintext federation acknowledgement.</dd>
</div>

<div>
<dt><code>STIGMEM_LOCAL_DEV_ALLOW_INSECURE_NON_LOOPBACK</code></dt>
<dt><span className="stigmem-fields__type"><code>1</code></span></dt>
<dd>Allows local Docker service DNS names (<code>node-a</code>, <code>node-b</code>) for the plaintext demo.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code></dt>
<dt><span className="stigmem-fields__type"><code>30</code></span></dt>
<dd>Seconds between pull cycles.</dd>
</div>

<div>
<dt><code>STIGMEM_SECRET_KEY</code></dt>
<dt><span className="stigmem-fields__type">auto-generated</span></dt>
<dd>Ed25519 private key seed — persist this across restarts.</dd>
</div>

</div>

To customize, copy `docker-compose.yml` and edit the `environment:`
block before running.

<div className="stigmem-keypoint">

**Production checklist.**

Remove both insecure local-dev flags
(<code>STIGMEM_FEDERATION_INSECURE</code> and
<code>STIGMEM_LOCAL_DEV_ALLOW_INSECURE_NON_LOOPBACK</code>) and
configure mTLS per
[mTLS federation transport](../security/mtls.md) before peering
outside localhost.

</div>

## 4-node topology (soak / staging)

For multi-node deployments, use the soak Compose file:

```bash
docker compose -f infra/docker-compose.soak.yml up --build -d
```

This starts four nodes (`node-a` through `node-d` on ports 8765–8768)
in a full-mesh topology. See the
[4-node topology guide](../concepts/federation/federation-4node) for
peer wiring, failure injection, and soak metrics.

## Path B · Running without Docker (development)

For development against the source directly:

```bash
cd stigmem/node
pip install -e .      # or: uv sync
python -m stigmem_node
```

The node starts on `http://localhost:8000`. Interactive Swagger UI at
`http://localhost:8000/docs`.

## Running as a persistent service (macOS)

The `service-install.sh` script registers Stigmem as a macOS
LaunchAgent that starts automatically at login and restarts on crash
— no Docker required.

### Prerequisites

A Python venv built in the repo root (run `uv sync` if you haven't
already):

```bash
uv sync
```

The script expects `.venv/bin/stigmem-node` to exist; it will fail
fast if it doesn't.

### Install

```bash
bash scripts/service-install.sh
```

The script:

<ol className="stigmem-steps">
<li>Generates a LaunchAgent plist at <code>~/Library/LaunchAgents/com.eidetic-labs.stigmem.plist</code>.</li>
<li>Bootstraps it with <code>launchctl bootstrap</code> (no <code>sudo</code> required).</li>
<li>Polls <code>http://127.0.0.1:8765/healthz</code> for up to 10 seconds and prints the result.</li>
</ol>

The service runs with these environment variables baked in:

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Value</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>STIGMEM_HOST</code></dt>
<dt><span className="stigmem-fields__type"><code>127.0.0.1</code></span></dt>
<dd>Localhost-only bind.</dd>
</div>

<div>
<dt><code>STIGMEM_PORT</code></dt>
<dt><span className="stigmem-fields__type"><code>8765</code></span></dt>
<dd>Default port.</dd>
</div>

<div>
<dt><code>STIGMEM_DB_PATH</code></dt>
<dt><span className="stigmem-fields__type"><code>data/stigmem.db</code></span></dt>
<dd>Relative to the repo root.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ENABLED</code></dt>
<dt><span className="stigmem-fields__type"><code>false</code></span></dt>
<dd>Standalone node only — no federation peering by default.</dd>
</div>

</div>

Logs are written to `logs/stigmem.log` (stdout) and
`logs/stigmem-error.log` (stderr).

### Verify

```bash
curl -s http://127.0.0.1:8765/healthz   # {"status":"ok"}
lsof -i :8765                           # shows the stigmem-node process
```

### Uninstall

```bash
bash scripts/service-uninstall.sh
```

Stops the service, unregisters it from `launchctl`, and removes the
plist. The database at `data/stigmem.db` is preserved.

:::note
The service label is `com.eidetic-labs.stigmem`. To inspect it directly:
```bash
launchctl print gui/$(id -u)/com.eidetic-labs.stigmem
```
:::

## Upgrading

```bash
git pull
docker compose up --build -d   # rebuilds the image from updated source
```

Data volumes persist across rebuilds. Run database migrations
automatically on startup — there is no manual migration step.

## Teardown

```bash
docker compose down      # stop containers; preserve data volumes
docker compose down -v   # stop and delete all data volumes
```

## What's next

<div className="stigmem-next">

<a href="./quickstart-tutorial">
<strong>Step 2</strong>
<span>Quickstart tutorial</span>
<small>Assert your first fact, query it back, watch a conflict open.</small>
</a>

<a href="./sdk-quickstart">
<strong>Step 3</strong>
<span>SDK quickstart</span>
<small>Connect from Python, TypeScript, or Go.</small>
</a>

<a href="../security/mtls">
<strong>Read</strong>
<span>mTLS federation transport</span>
<small>What changes when you leave the local-dev defaults.</small>
</a>

</div>
