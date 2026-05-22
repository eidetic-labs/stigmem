---
title: Deployment & Installation
sidebar_label: Install
audience: Operator
---

# Deployment & Installation

<p className="stigmem-meta"><span>6 min read</span><span>First-time operator</span><span>v0.9.0a1</span></p>

<div className="stigmem-lead">

**What this page covers**

How to install the Stigmem reference node. Docker Compose is the
supported deployment path in v0.9.0a1 for both local development
and single-host production. For development against source, see
[Running without Docker](#running-without-docker).

</div>

**Audience:** node operators installing Stigmem for the first time, or migrating an existing bare-metal install to Docker.

:::tip Operator handbook
For the narrative Docker Compose runbook, see **[Operating Stigmem → Deploy runbooks](../runbooks/deploy-runbooks)**.
:::

:::caution Other deployment surfaces are deferred
Fly.io, Helm/Kubernetes, systemd, PaaS, and Grafana recipes have been moved to [`experimental/deploy-*/`](https://github.com/eidetic-labs/stigmem/tree/main/experimental) per [ADR-002](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/002-v1-scope.md). They remain available as starting points but are unsupported until they pass the [ADR-008 reintroduction gates](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/008-experimental-gates.md). See **[Features → Deployment](../../concepts/features#operations-v090a1-critical-path)** for the full disposition.
:::

## Container image tags — which one should I pull? {#image-tags}

The reference node image is published to GHCR at [`ghcr.io/eidetic-labs/stigmem-node`](https://github.com/eidetic-labs/stigmem/pkgs/container/stigmem-node). Several tag flavours are published in parallel.

<div className="stigmem-fields">

<div>
<dt>Tag</dt>
<dt><span className="stigmem-fields__type">Stability</span></dt>
<dd>Use when</dd>
</div>

<div>
<dt><code>:0.9.0aN</code> / <code>:0.9.0bN</code> / <code>:1.0.0rcN</code> / <code>:1.0.0</code></dt>
<dt><span className="stigmem-fields__type">immutable</span></dt>
<dd><strong>Release-pinned evaluation or controlled internal workloads.</strong> Never reassigned after publish. Reproducible builds, audit-traceable deployments, change-control gates. Do not treat alpha tags as production-stable.</dd>
</div>

<div>
<dt><code>:0.9.0-alpha.N</code> / <code>:0.9.0-beta.N</code> / <code>:1.0.0-rc.N</code></dt>
<dt><span className="stigmem-fields__type">immutable</span></dt>
<dd>Same artefact in semver-strict spelling. Use whichever your tooling prefers.</dd>
</div>

<div>
<dt><code>:latest</code></dt>
<dt><span className="stigmem-fields__type">rolling (release tags)</span></dt>
<dd>Quickstart, eval, demos. You accept that the image will silently advance when a new release ships.</dd>
</div>

<div>
<dt><code>:edge</code></dt>
<dt><span className="stigmem-fields__type">rolling (every main push)</span></dt>
<dd>Tracking tip-of-trunk between releases. CI-tested but not release-gated.</dd>
</div>

<div>
<dt><code>:&lt;short-sha&gt;</code></dt>
<dt><span className="stigmem-fields__type">immutable (90 days)</span></dt>
<dd>Forensics, rollback to a specific commit, reproducing a CI failure.</dd>
</div>

<div>
<dt><code>@sha256:&lt;digest&gt;</code></dt>
<dt><span className="stigmem-fields__type">tamper-evident</span></dt>
<dd><strong>Supply-chain-conscious deployments.</strong> Fixes the content, not the label. Required for hardened production once the release line is stable.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Quick rule of thumb**

- Trying things out → `:latest`
- Controlled internal workload → `:0.9.0aN` (your current release)
- Auditable deployment → `@sha256:<digest>` of the version tag you intend to run

</div>

:::tip Verifying what `:latest` resolves to today
```bash
docker pull ghcr.io/eidetic-labs/stigmem-node:latest
docker inspect --format '{{.RepoDigests}}' ghcr.io/eidetic-labs/stigmem-node:latest
```
The printed digest is what's actually running. Pin to that digest in your Compose / Helm chart for a tamper-evident production deployment.
:::

### Image retention {#image-retention}

<div className="stigmem-grid">

<div><h4>Retained forever</h4><p><code>:latest</code>; all version tags (<code>:0.9.0aN</code>, <code>:0.9.0bN</code>, <code>:1.0.0rcN</code>, <code>:1.0.0</code>); <code>:edge</code>.</p></div>
<div><h4>Retained 90 days</h4><p>Short-SHA tags and their orphan Sigstore signature artefacts.</p></div>

</div>

Operationally enforced by [`.github/workflows/ghcr-retention.yml`](https://github.com/eidetic-labs/stigmem/blob/main/.github/workflows/ghcr-retention.yml).

## Prerequisites

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Minimum</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Docker</dt>
<dt><span className="stigmem-fields__type">≥ 24</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Docker Compose (v2)</dt>
<dt><span className="stigmem-fields__type">≥ 2.20</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Git</dt>
<dt><span className="stigmem-fields__type">any recent</span></dt>
<dd>—</dd>
</div>

</div>

No Python or Node.js installation is required for the Docker path.

## One-click Docker Compose install

```bash
git clone https://github.com/eidetic-labs/stigmem
cd stigmem
docker compose up --build -d
```

This builds the reference node image once and starts `node-a` and `node-b`:

<div className="stigmem-fields">

<div>
<dt>Container</dt>
<dt><span className="stigmem-fields__type">Host port</span></dt>
<dd>Key endpoints</dd>
</div>

<div>
<dt><code>node-a</code></dt>
<dt><span className="stigmem-fields__type">8765</span></dt>
<dd><code>/healthz</code> · <code>/docs</code> · <code>/.well-known/stigmem</code></dd>
</div>

<div>
<dt><code>node-b</code></dt>
<dt><span className="stigmem-fields__type">8766</span></dt>
<dd><code>/healthz</code> · <code>/docs</code> · <code>/.well-known/stigmem</code></dd>
</div>

</div>

Verify both are healthy:

```bash
curl -s http://localhost:8765/healthz   # → {"status":"ok"}
curl -s http://localhost:8766/healthz   # → {"status":"ok"}
```

Then follow the [Quickstart](../../get-started/quickstart-tutorial) to complete the federation handshake and assert your first fact.

### Persist your keypairs

By default, each node auto-generates an Ed25519 keypair on first start and stores it in `node_meta`. To survive container recreation, supply your own:

```bash
python3 -c "
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import base64, os
priv = Ed25519PrivateKey.generate()
priv_bytes = priv.private_bytes_raw()
pub_bytes  = priv.public_key().public_bytes_raw()
print('STIGMEM_FEDERATION_PRIVKEY=' + base64.urlsafe_b64encode(priv_bytes).decode())
print('STIGMEM_FEDERATION_PUBKEY='  + base64.urlsafe_b64encode(pub_bytes).decode())
"
```

Add those two variables to the `environment:` block of your `docker-compose.yml`.

### Stop and clean up

```bash
docker compose down      # stop containers; preserve data volumes
docker compose down -v   # stop and delete all data
```

## Multi-node topology (soak / staging)

For 4-node full-mesh federation with shorter pull intervals:

```bash
# Generate keypairs for all four nodes
cd infra && python soak/keys.py > soak/.env

# Start the cluster
docker compose -f infra/docker-compose.soak.yml --env-file infra/soak/.env up --build -d
```

Nodes run on ports 8765–8768. See the [4-node federation guide](../../concepts/federation/federation-4node) for peer wiring, backpressure, and failure injection.

## Environment variable reference

### Core

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_DB_PATH</code></dt>
<dt><span className="stigmem-fields__type">stigmem.db</span></dt>
<dd>Path to the SQLite database file.</dd>
</div>

<div>
<dt><code>STIGMEM_HOST</code></dt>
<dt><span className="stigmem-fields__type">0.0.0.0</span></dt>
<dd>Bind address.</dd>
</div>

<div>
<dt><code>STIGMEM_PORT</code></dt>
<dt><span className="stigmem-fields__type">8765</span></dt>
<dd>HTTP listen port.</dd>
</div>

<div>
<dt><code>STIGMEM_NODE_URL</code></dt>
<dt><span className="stigmem-fields__type">http://localhost:8765</span></dt>
<dd>Public URL of this node — included in <code>PeerDeclaration</code> payloads.</dd>
</div>

<div>
<dt><code>STIGMEM_LOG_LEVEL</code></dt>
<dt><span className="stigmem-fields__type">info</span></dt>
<dd>debug · info · warning · error.</dd>
</div>

<div>
<dt><code>STIGMEM_AUTH_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type">true</span></dt>
<dd>Every request must carry a valid Bearer token. Set <code>false</code> only for single-operator / local-only installs.</dd>
</div>

</div>

### Federation

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Enable the pull-replication loop.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PUBKEY</code></dt>
<dt><span className="stigmem-fields__type">"" (auto)</span></dt>
<dd>Base64url Ed25519 public key. <strong>Persist this.</strong></dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PRIVKEY</code></dt>
<dt><span className="stigmem-fields__type">"" (auto)</span></dt>
<dd>Base64url Ed25519 private key. <strong>Persist this.</strong></dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PULL_INTERVAL_S</code></dt>
<dt><span className="stigmem-fields__type">30</span></dt>
<dd>Seconds between pull cycles. Peer-advertised value takes precedence.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_PUSH_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Enable push replication (experimental).</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_NONCE_WINDOW_S</code></dt>
<dt><span className="stigmem-fields__type">300</span></dt>
<dd>How long a nonce is retained to block replays.</dd>
</div>

<div>
<dt><code>STIGMEM_FEDERATION_ALLOW_TEAM</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Allow <code>team</code>-scoped facts to cross federation boundaries. Audit-logged.</dd>
</div>

</div>

### Decay, Attestation, OIDC, Performance

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Default</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_DECAY_TTL_SECONDS</code></dt>
<dt><span className="stigmem-fields__type">0 (disabled)</span></dt>
<dd>Default TTL when a sweep runs without an explicit <code>ttl_seconds</code>.</dd>
</div>

<div>
<dt><code>STIGMEM_DECAY_MIN_CONFIDENCE</code></dt>
<dt><span className="stigmem-fields__type">0.0 (disabled)</span></dt>
<dd>Default minimum confidence for decay sweeps.</dd>
</div>

<div>
<dt><code>STIGMEM_ATTESTATION_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Require Ed25519 attestation token on every <code>POST /v1/facts</code>. Enable for multi-tenant or public nodes.</dd>
</div>

<div>
<dt><code>STIGMEM_SOURCE_ATTESTATION_MODE</code></dt>
<dt><span className="stigmem-fields__type">off</span></dt>
<dd>Legacy compatibility field. Use the experimental source-attestation plugin plus explicit plugin gates for runtime enforcement.</dd>
</div>

<div>
<dt><code>STIGMEM_OIDC_ENABLED</code></dt>
<dt><span className="stigmem-fields__type">false</span></dt>
<dd>Enable the OIDC → API key bridge.</dd>
</div>

<div>
<dt><code>STIGMEM_OIDC_ISSUER_URL</code></dt>
<dt><span className="stigmem-fields__type">""</span></dt>
<dd>IdP issuer URL.</dd>
</div>

<div>
<dt><code>STIGMEM_OIDC_AUDIENCE</code></dt>
<dt><span className="stigmem-fields__type">""</span></dt>
<dd>Expected <code>aud</code> claim.</dd>
</div>

<div>
<dt><code>STIGMEM_OIDC_TOKEN_TTL_HOURS</code></dt>
<dt><span className="stigmem-fields__type">8</span></dt>
<dd>Lifetime of issued API keys.</dd>
</div>

<div>
<dt><code>STIGMEM_OIDC_ALLOWED_DOMAINS</code></dt>
<dt><span className="stigmem-fields__type">"" (any)</span></dt>
<dd>Comma-separated allowed email domains.</dd>
</div>

<div>
<dt><code>STIGMEM_ASYNC_JOB_THRESHOLD</code></dt>
<dt><span className="stigmem-fields__type">100000</span></dt>
<dd>Fact count per scope above which decay sweep returns <code>202 Accepted</code>.</dd>
</div>

</div>

## Upgrade

### Upgrading a Docker Compose install

```bash
git pull
docker compose up --build -d
```

<div className="stigmem-keypoint">

**Data volumes persist across rebuilds. Database migrations run automatically on startup — there is no manual migration step.**

</div>

### Upgrading from bare-metal to Docker Compose

<ol className="stigmem-steps">
<li><strong>Stop the existing service.</strong> If running as a macOS LaunchAgent: <code>bash scripts/service-uninstall.sh</code>. If running manually, stop the process (Ctrl-C or kill the PID).</li>
<li><strong>Locate your database.</strong> By default the bare-metal node writes to <code>data/stigmem.db</code> (relative to the repo root). <code>ls -lh data/stigmem.db</code>. If you set <code>STIGMEM_DB_PATH</code>, use that path instead.</li>
<li><strong>Create a Docker volume and copy data in</strong> (see snippet below).</li>
<li><strong>Start Docker Compose.</strong> <code>docker compose up --build -d</code>. Verify node-a picked up the data: <code>curl -s 'http://localhost:8765/v1/facts?limit=5' | jq .facts</code></li>
<li><strong>(Optional) Restore your keypair.</strong> If you had a stable <code>STIGMEM_FEDERATION_PUBKEY</code>/<code>PRIVKEY</code>, add the same values to <code>docker-compose.yml</code> so existing peers recognize the node.</li>
</ol>

```bash
# Create the named volumes Docker Compose expects
docker volume create stigmem__node-a-data
docker volume create stigmem__node-b-data

# Copy your existing database into node-a's volume
docker run --rm \
  -v "$(pwd)/data/stigmem.db:/src/stigmem.db:ro" \
  -v "stigmem__node-a-data:/data" \
  busybox cp /src/stigmem.db /data/stigmem.db
```

:::note Volume naming
Docker Compose prefixes volume names with the project name (derived from the directory name). If your repo directory is not named `stigmem`, replace `stigmem__` with `<directory-name>_`.
:::

## Running without Docker

For development against the source directly:

```bash
cd stigmem/node
uv sync                          # install dependencies
uv run python -m stigmem_node    # starts on http://localhost:8765
```

Interactive Swagger UI: `http://localhost:8765/docs`.

For macOS persistent service (LaunchAgent, no Docker), see [Installation](../../get-started/installation#running-as-a-persistent-service-macos).
