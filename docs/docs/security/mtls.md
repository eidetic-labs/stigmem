---
title: mTLS Federation Transport
sidebar_label: mTLS
description: Configure mutual TLS for Stigmem federation — cert provisioning, rotation, cipher policy, and deployment recipes.
audience: Operator
---

# mTLS Federation Transport

Stigmem nodes use **mutual TLS (mTLS)** for all federation peer-to-peer traffic — replication pulls, push wakes, and capability-token exchanges.  This is a normative requirement of Spec-10-Hardening for any deployment that connects more than one node.

> **Explicit local/dev/test opt-out.** Federation startup requires mTLS by
> default. Leave `STIGMEM_TLS_CERT_PATH` / `STIGMEM_TLS_KEY_PATH` unset only for
> local/dev/test federation and only with `STIGMEM_FEDERATION_INSECURE=1`. The
> node logs a security warning while that flag is active.

---

## How it works

When `STIGMEM_TLS_CERT_PATH` and `STIGMEM_TLS_KEY_PATH` are set:

1. **Server**: Uvicorn starts with TLS 1.3 and requires a client certificate from every peer (`ssl.CERT_REQUIRED`).  Plaintext TCP connections to the federation port are rejected at the TLS handshake — no HTTP response is sent.
2. **Client (pull loop)**: The pull-replication background task creates an `httpx.AsyncClient` that presents the node's cert and verifies the peer's cert against `STIGMEM_TLS_CA_BUNDLE`.
3. **Cert watcher**: A background task polls `STIGMEM_TLS_CERT_PATH` every 5 seconds.  When the mtime changes, it calls `ssl.SSLContext.load_cert_chain()` on the live context — in-flight connections are unaffected; new handshakes pick up the new cert immediately.
4. **SIGHUP**: Sending `SIGHUP` to the node process triggers an immediate cert reload (same mechanism as the file watcher).

### Cipher policy (Spec-10-Hardening.2.3)

TLS 1.3 is enforced as the minimum protocol version.  The permitted cipher suites are:

| Suite | IANA name |
|---|---|
| TLS_AES_256_GCM_SHA384 | Required |
| TLS_AES_128_GCM_SHA256 | Required |
| TLS_CHACHA20_POLY1305_SHA256 | Required |

TLS 1.2 and earlier are **not** negotiated on federation ports.

### Insecure local/dev/test mode

If `STIGMEM_FEDERATION_ENABLED=true` or `STIGMEM_FEDERATION_PUSH_ENABLED=true`
and the TLS cert/key paths are unset, the node refuses to start unless
`STIGMEM_FEDERATION_INSECURE=1` is also set. Use that flag only for local
single-machine tests or development fixtures. It does not provide peer
authentication and is not a production setting.

### SAN validation (Spec-10-Hardening.2.4)

After each successful handshake, the node verifies that the peer certificate's `subjectAltName` contains a **URI SAN** matching the peer's `entity_uri` as declared in its org manifest (`/.well-known/stigmem-manifest.json`).  Connections where the SAN does not match are rejected with a structured JSON error before any federation data is exchanged.

---

## Configuration

| Variable | Required | Description |
|---|---|---|
| `STIGMEM_TLS_CERT_PATH` | Yes (non-localhost) | Path to the node's PEM X.509 certificate |
| `STIGMEM_TLS_KEY_PATH` | Yes (non-localhost) | Path to the corresponding PEM private key |
| `STIGMEM_TLS_CA_BUNDLE` | Recommended | Path to a PEM CA bundle for verifying peer certs |

All three paths are resolved at startup.  The node refuses to start if the cert/key files are unreadable.

---

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

Repeat step 2 for each node, using its own `ENTITY_URI`.  All nodes in the federation share the same CA certificate in their `STIGMEM_TLS_CA_BUNDLE`.

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

cert-manager rotates the secret automatically.  Stigmem's cert watcher detects the mtime change and reloads within 5 seconds — no pod restart required.

---

## Certificate rotation (Spec-10-Hardening.3)

### Zero-downtime rotation procedure

1. **Generate the new certificate** (same CA, new key pair, same `entity_uri` URI SAN).
2. **Update the org manifest** — record the new cert's public-key fingerprint as a `tls_cert_fingerprint` field in `/.well-known/stigmem-manifest.json` and re-sign the manifest.
3. **Submit the updated manifest to the transparency log** and wait for acknowledgement before activating the new cert.
4. **Replace the cert files** at `STIGMEM_TLS_CERT_PATH` / `STIGMEM_TLS_KEY_PATH`.
5. **Signal the node** to reload: either wait for the 5-second file watcher or send `SIGHUP`:

   ```bash
   kill -HUP $(cat /var/run/stigmem.pid)
   ```

6. **Dual-trust window**: During the rotation, federation peers may see either the old or the new certificate depending on timing.  Both are signed by the same CA, so peer verification succeeds throughout.  See Spec-10-Hardening.3.5 and Spec-10-Hardening dual-trust window for the dual-trust period requirements (minimum 90 days for capability tokens).

### Verifying rotation

```bash
# Check which cert the node is currently presenting
openssl s_client -connect your-node:8765 \
  -cert client.crt -key client.key \
  -CAfile ca.crt 2>/dev/null | openssl x509 -noout -fingerprint -dates
```

---

## Reverse proxy deployments

> **Out of scope for this how-to.** If TLS is terminated at the proxy (nginx, Caddy, HAProxy), configure mTLS there and leave `STIGMEM_TLS_CERT_PATH` unset.  See the [deploy runbooks](../operators/runbooks/deploy-runbooks.md) for proxy-pass recipes.  Note that proxy-terminated mTLS does not provide end-to-end mutual authentication between Stigmem nodes — peer-cert SAN validation must be performed at the proxy or re-verified at the app layer.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ssl.SSLError: CERTIFICATE_VERIFY_FAILED` | Peer cert not signed by a CA in `STIGMEM_TLS_CA_BUNDLE` | Add peer's CA cert to the bundle and reload |
| `ssl.SSLError: NO_SHARED_CIPHER` | TLS version mismatch (peer uses TLS 1.2) | Upgrade peer to a Stigmem version that supports TLS 1.3 |
| `ssl.SSLError: CERTIFICATE_REQUIRED` | Peer is not presenting a client cert | Peer node needs `STIGMEM_TLS_CERT_PATH` / `STIGMEM_TLS_KEY_PATH` configured |
| Federation routes return `421` | mTLS enabled but request arrived over HTTP | Ensure clients connect via HTTPS; check reverse proxy TLS passthrough config |
| Cert watcher not reloading | File mtime not updating (symlink rotation) | Use `kill -HUP` instead; or ensure rotation replaces the file at the same path |
