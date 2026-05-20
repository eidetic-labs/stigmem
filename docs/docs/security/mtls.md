---
title: mTLS Federation Transport
sidebar_label: mTLS
description: Configure mutual TLS for Stigmem federation — cert provisioning, rotation, cipher policy, and deployment recipes.
audience: Operator
---

# mTLS Federation Transport

<p className="stigmem-meta"><span>5 min read</span><span>Operator</span><span>Spec-10-Hardening</span></p>

<div className="stigmem-lead">

**What this page is**

Stigmem nodes use **mutual TLS (mTLS)** for all federation
peer-to-peer traffic — replication pulls, push wakes, and
capability-token exchanges. This is a normative requirement of
Spec-10-Hardening for any deployment that connects more than one node.

</div>

<div className="stigmem-keypoint">

**Explicit local/dev/test opt-out.**

Federation startup requires mTLS by default. Leave
<code>STIGMEM_TLS_CERT_PATH</code> / <code>STIGMEM_TLS_KEY_PATH</code>
unset only for local/dev/test federation and only with
<code>STIGMEM_FEDERATION_INSECURE=1</code>. The node logs a security
warning while that flag is active.

</div>

## How it works

When `STIGMEM_TLS_CERT_PATH` and `STIGMEM_TLS_KEY_PATH` are set:

<ol className="stigmem-steps">
<li><strong>Server.</strong> Uvicorn starts with TLS 1.3 and requires a client certificate from every peer (<code>ssl.CERT_REQUIRED</code>). Plaintext TCP connections to the federation port are rejected at the TLS handshake — no HTTP response is sent.</li>
<li><strong>Client (pull loop).</strong> The pull-replication background task creates an <code>httpx.AsyncClient</code> that presents the node's cert and verifies the peer's cert against <code>STIGMEM_TLS_CA_BUNDLE</code>.</li>
<li><strong>Cert watcher.</strong> A background task polls <code>STIGMEM_TLS_CERT_PATH</code> every 5 seconds. When the mtime changes, it calls <code>ssl.SSLContext.load_cert_chain()</code> on the live context — in-flight connections are unaffected; new handshakes pick up the new cert immediately.</li>
<li><strong>SIGHUP.</strong> Sending <code>SIGHUP</code> to the node process triggers an immediate cert reload (same mechanism as the file watcher).</li>
</ol>

### Cipher policy (Spec-10-Hardening.2.3)

TLS 1.3 is enforced as the minimum protocol version. The permitted
cipher suites are:

<div className="stigmem-fields">

<div>
<dt>Suite</dt>
<dt><span className="stigmem-fields__type">IANA name</span></dt>
<dd>Status</dd>
</div>

<div>
<dt><code>TLS_AES_256_GCM_SHA384</code></dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd></dd>
</div>

<div>
<dt><code>TLS_AES_128_GCM_SHA256</code></dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd></dd>
</div>

<div>
<dt><code>TLS_CHACHA20_POLY1305_SHA256</code></dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd></dd>
</div>

</div>

TLS 1.2 and earlier are **not** negotiated on federation ports.

### Insecure local/dev/test mode

If `STIGMEM_FEDERATION_ENABLED=true` or
`STIGMEM_FEDERATION_PUSH_ENABLED=true` and the TLS cert/key paths are
unset, the node refuses to start unless
`STIGMEM_FEDERATION_INSECURE=1` is also set. Use that flag only for
local single-machine tests or development fixtures. It does not
provide peer authentication and is not a production setting.

When a local Docker demo uses service DNS names such as `node-a` or
`node-b`, the node also requires
`STIGMEM_LOCAL_DEV_ALLOW_INSECURE_NON_LOOPBACK=1`. That second
acknowledgement is only for local Docker/dev networks; production
non-loopback federation must use mTLS.

### SAN validation (Spec-10-Hardening.2.4)

After each successful handshake, the node verifies that the peer
certificate's `subjectAltName` contains a **URI SAN** matching the
peer's `entity_uri` as declared in its org manifest
(`/.well-known/stigmem-manifest.json`). Connections where the SAN
does not match are rejected with a structured JSON error before any
federation data is exchanged.

## Configuration

<div className="stigmem-fields">

<div>
<dt>Variable</dt>
<dt><span className="stigmem-fields__type">Required?</span></dt>
<dd>Description</dd>
</div>

<div>
<dt><code>STIGMEM_TLS_CERT_PATH</code></dt>
<dt><span className="stigmem-fields__type">Yes (non-localhost)</span></dt>
<dd>Path to the node's PEM X.509 certificate.</dd>
</div>

<div>
<dt><code>STIGMEM_TLS_KEY_PATH</code></dt>
<dt><span className="stigmem-fields__type">Yes (non-localhost)</span></dt>
<dd>Path to the corresponding PEM private key.</dd>
</div>

<div>
<dt><code>STIGMEM_TLS_CA_BUNDLE</code></dt>
<dt><span className="stigmem-fields__type">Recommended</span></dt>
<dd>Path to a PEM CA bundle for verifying peer certs.</dd>
</div>

</div>

All three paths are resolved at startup. The node refuses to start if
the cert/key files are unreadable.

## Provisioning node certificates

### Self-managed CA (recommended for small clusters)

```bash
# 1. Generate a federation CA (do this once, store securely)
openssl genpkey -algorithm ed25519 -out ca.key
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 \
  -subj "/CN=Stigmem Federation CA"

# 2. Generate a node cert with the entity_uri as URI SAN
#    Replace ENTITY_URI with your node's canonical entity URI.
ENTITY_URI="stigmem://your-org.example.com/nodes/primary"

openssl genpkey -algorithm ed25519 -out node.key
openssl req -new -key node.key -out node.csr \
  -subj "/CN=stigmem-node" \
  -addext "subjectAltName=URI:${ENTITY_URI}"
openssl x509 -req -in node.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out node.crt -days 90 \
  -extfile <(echo "subjectAltName=URI:${ENTITY_URI}")

# 3. Configure the node
export STIGMEM_TLS_CERT_PATH=/etc/stigmem/tls/node.crt
export STIGMEM_TLS_KEY_PATH=/etc/stigmem/tls/node.key
export STIGMEM_TLS_CA_BUNDLE=/etc/stigmem/tls/ca.crt
```

Repeat step 2 for each node, using its own `ENTITY_URI`. All nodes in
the federation share the same CA certificate in their
`STIGMEM_TLS_CA_BUNDLE`.

### Docker Compose mTLS example

The local plaintext quickstart remains available for contributor smoke
tests, but production-shaped federation should use mTLS. The compose
example under `deploy/compose/docker-compose.mtls.yml` mounts a
generated CA bundle plus one node certificate/key pair per service
and leaves `STIGMEM_FEDERATION_INSECURE` unset.

```bash
./deploy/compose/generate-mtls-demo-certs.sh
docker compose -f deploy/compose/docker-compose.mtls.yml up -d --build
```

For an end-to-end local validation that includes peer registration and
fact replication, run:

```bash
bash scripts/mtls-compose-smoke.sh
```

The smoke script creates local-only certificate material in a temp
directory, starts the compose stack without
`STIGMEM_FEDERATION_INSECURE`, verifies both nodes over HTTPS with
client certificates, registers peers, asserts a fact on node A,
verifies the fact on node B, and removes containers and volumes
unless `KEEP_UP=1`.

Verify the nodes with the generated client certificates:

```bash
curl --cacert deploy/compose/tls/ca.crt \
  --cert deploy/compose/tls/node-a.crt \
  --key deploy/compose/tls/node-a.key \
  --resolve stigmem-a:8765:127.0.0.1 \
  https://stigmem-a:8765/healthz

curl --cacert deploy/compose/tls/ca.crt \
  --cert deploy/compose/tls/node-b.crt \
  --key deploy/compose/tls/node-b.key \
  --resolve stigmem-b:8766:127.0.0.1 \
  https://stigmem-b:8766/healthz
```

The generated certificates are suitable only for local validation.
For a real deployment, issue node certificates from your federation
CA and keep the service DNS SAN plus the node `entity_uri` URI SAN.

### cert-manager (Kubernetes)

```yaml
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: stigmem-node-tls
  namespace: stigmem
spec:
  secretName: stigmem-node-tls
  duration: 24h         # short-lived as recommended by Spec-10-Hardening.4
  renewBefore: 8h
  issuerRef:
    name: stigmem-ca-issuer
    kind: ClusterIssuer
  usages:
    - client auth
    - server auth
  uris:
    - "stigmem://your-org.example.com/nodes/primary"   # entity_uri as URI SAN
```

Mount the secret and set env vars:

```yaml
env:
  - name: STIGMEM_TLS_CERT_PATH
    value: /tls/tls.crt
  - name: STIGMEM_TLS_KEY_PATH
    value: /tls/tls.key
  - name: STIGMEM_TLS_CA_BUNDLE
    value: /tls/ca.crt
volumeMounts:
  - name: tls
    mountPath: /tls
    readOnly: true
```

cert-manager rotates the secret automatically. Stigmem's cert watcher
detects the mtime change and reloads within 5 seconds — no pod
restart required.

## Certificate rotation (Spec-10-Hardening.3)

### Zero-downtime rotation procedure

<ol className="stigmem-steps">
<li><strong>Generate the new certificate</strong> (same CA, new key pair, same <code>entity_uri</code> URI SAN).</li>
<li><strong>Update the org manifest</strong> — record the new cert's public-key fingerprint as a <code>tls_cert_fingerprint</code> field in <code>/.well-known/stigmem-manifest.json</code> and re-sign the manifest.</li>
<li><strong>Submit the updated manifest to the transparency log</strong> and wait for acknowledgement before activating the new cert.</li>
<li><strong>Replace the cert files</strong> at <code>STIGMEM_TLS_CERT_PATH</code> / <code>STIGMEM_TLS_KEY_PATH</code>.</li>
<li><strong>Signal the node</strong> to reload: either wait for the 5-second file watcher or send <code>SIGHUP</code>: <code>kill -HUP $(cat /var/run/stigmem.pid)</code>.</li>
<li><strong>Dual-trust window.</strong> During rotation, federation peers may see either the old or the new certificate depending on timing. Both are signed by the same CA, so peer verification succeeds throughout. See Spec-10-Hardening.3.5 (minimum 90 days for capability tokens).</li>
</ol>

### Verifying rotation

```bash
# Check which cert the node is currently presenting
openssl s_client -connect your-node:8765 \
  -cert client.crt -key client.key \
  -CAfile ca.crt 2>/dev/null | openssl x509 -noout -fingerprint -dates
```

## Reverse proxy deployments

<div className="stigmem-keypoint">

**Out of scope for this how-to.**

If TLS is terminated at the proxy (nginx, Caddy, HAProxy), configure
mTLS there and leave <code>STIGMEM_TLS_CERT_PATH</code> unset. See the
<a href="../operators/runbooks/deploy-runbooks">deploy runbooks</a>
for proxy-pass recipes. Note that proxy-terminated mTLS does not
provide end-to-end mutual authentication between Stigmem nodes —
peer-cert SAN validation must be performed at the proxy or
re-verified at the app layer.

</div>

## Troubleshooting

<div className="stigmem-fields">

<div>
<dt>Symptom</dt>
<dt><span className="stigmem-fields__type">Likely cause</span></dt>
<dd>Fix</dd>
</div>

<div>
<dt><code>ssl.SSLError: CERTIFICATE_VERIFY_FAILED</code></dt>
<dt><span className="stigmem-fields__type">peer cert not signed by trusted CA</span></dt>
<dd>Add peer's CA cert to <code>STIGMEM_TLS_CA_BUNDLE</code> and reload.</dd>
</div>

<div>
<dt><code>ssl.SSLError: NO_SHARED_CIPHER</code></dt>
<dt><span className="stigmem-fields__type">TLS version mismatch</span></dt>
<dd>Peer uses TLS 1.2; upgrade peer to a Stigmem version that supports TLS 1.3.</dd>
</div>

<div>
<dt><code>ssl.SSLError: CERTIFICATE_REQUIRED</code></dt>
<dt><span className="stigmem-fields__type">peer not presenting a client cert</span></dt>
<dd>Peer node needs <code>STIGMEM_TLS_CERT_PATH</code> / <code>STIGMEM_TLS_KEY_PATH</code> configured.</dd>
</div>

<div>
<dt>Federation routes return <code>421</code></dt>
<dt><span className="stigmem-fields__type">mTLS enabled, request over HTTP</span></dt>
<dd>Ensure clients connect via HTTPS; check reverse proxy TLS passthrough config.</dd>
</div>

<div>
<dt>Cert watcher not reloading</dt>
<dt><span className="stigmem-fields__type">file mtime not updating</span></dt>
<dd>Symlink rotation hides the mtime change. Use <code>kill -HUP</code> instead; or ensure rotation replaces the file at the same path.</dd>
</div>

</div>
