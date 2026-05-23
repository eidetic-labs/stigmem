---
title: "Tutorial: Harden a Stigmem Deployment"
sidebar_label: Harden a Deployment
description: Walk an operator from a default Stigmem node to a pre-reset hardening–hardened deployment — mTLS, key rotation, per-principal quotas, and a distroless container — end to end.
audience: Integrator
---

# Tutorial: Harden a Stigmem Deployment

<p className="stigmem-meta"><span>45 min · tutorial</span><span>Node operator</span><span>Production-bound</span></p>

<div className="stigmem-lead">

**What you will build**

A running Stigmem node with mTLS federation, rotated Ed25519
identity and issuer keys, per-principal quotas tuned to your
baseline traffic, the hardened distroless container image, and an
operator plan for immutable evidence.

</div>

**Audience:** node operators running Stigmem in production or preparing for production.
**Time:** ~45 minutes.

**Prerequisites:**

<div className="stigmem-grid">

<div><h4>Stigmem v0.9.0a2</h4><p><code>ghcr.io/eidetic-labs/stigmem-node:0.9.0a2</code>. For hardened production, pin to a digest (<code>@sha256:&lt;digest&gt;</code>).</p></div>
<div><h4>Docker Compose</h4><p><code>docker compose version</code>.</p></div>
<div><h4>Tools</h4><p><code>openssl</code>, <code>curl</code>, <code>jq</code> available.</p></div>
<div><h4>Admin API key</h4><p><code>STIGMEM_ADMIN_KEY</code>.</p></div>

</div>

All commands run against a local Docker Compose node. Adapt `https://your-node.example.com` substitutions for a remote deployment.

## What you will do

<ol className="stigmem-steps">
<li><strong>mTLS:</strong> generate a federation CA and issue a node cert.</li>
<li><strong>mTLS:</strong> configure the node and verify mutual TLS.</li>
<li><strong>Key rotation:</strong> rotate the Ed25519 identity key.</li>
<li><strong>Key rotation:</strong> rotate the capability issuer key.</li>
<li><strong>Quotas:</strong> tune write/read ceilings and verify 429 behaviour.</li>
<li><strong>Audit:</strong> mint an <code>audit.read</code> key and confirm events are emitted.</li>
<li><strong>Container:</strong> switch to the hardened image and verify seccomp.</li>
<li><strong>Immutability:</strong> route evidence to WORM storage and plan TEE deployment.</li>
</ol>

## Step 1 — Generate a federation CA and node cert

Start with a self-managed CA (suitable for small clusters and test environments). For larger clusters, replace this step with a cert-manager `ClusterIssuer` — see [mTLS Federation Transport](../security/mtls.md#cert-manager-kubernetes).

```bash
# Create a working directory for TLS material
mkdir -p /etc/stigmem/tls && cd /etc/stigmem/tls

# Generate the federation CA (store ca.key securely — do this once)
openssl genpkey -algorithm ed25519 -out ca.key
openssl req -new -x509 -key ca.key -out ca.crt -days 3650 \
  -subj "/CN=Stigmem Federation CA"

# Set your node's entity URI — must match the value in your org manifest
ENTITY_URI="stigmem://your-org.example.com/nodes/primary"

# Generate a node keypair and a 90-day cert with the entity_uri as URI SAN
openssl genpkey -algorithm ed25519 -out node.key
openssl req -new -key node.key -out node.csr \
  -subj "/CN=stigmem-node" \
  -addext "subjectAltName=URI:${ENTITY_URI}"
openssl x509 -req -in node.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out node.crt -days 90 \
  -extfile <(echo "subjectAltName=URI:${ENTITY_URI}")

echo "CA and node cert generated."
openssl x509 -noout -subject -dates -ext subjectAltName -in node.crt
```

Expected output includes `URI:stigmem://your-org.example.com/nodes/primary` in the SAN field.

## Step 2 — Configure mTLS and verify

```yaml
# docker-compose.override.yml
services:
  stigmem-node:
    environment:
      STIGMEM_TLS_CERT_PATH: /tls/node.crt
      STIGMEM_TLS_KEY_PATH:  /tls/node.key
      STIGMEM_TLS_CA_BUNDLE: /tls/ca.crt
      STIGMEM_FEDERATION_INSECURE: "0"
    volumes:
      - /etc/stigmem/tls:/tls:ro
```

```bash
docker compose up -d
```

**Verify the node is presenting its cert:**

```bash
openssl s_client -connect localhost:8765 \
  -cert /etc/stigmem/tls/node.crt \
  -key  /etc/stigmem/tls/node.key \
  -CAfile /etc/stigmem/tls/ca.crt \
  2>/dev/null | openssl x509 -noout -fingerprint -subject
```

**Verify that a plaintext connection is rejected:**

```bash
curl http://localhost:8765/healthz 2>&1 | grep -i "empty reply\|SSL\|refused"
# Expect: connection refused or SSL handshake error — not an HTTP 200
```

<div className="stigmem-keypoint">

**Federation will not start without TLS settings unless `STIGMEM_FEDERATION_INSECURE=1` is explicitly set.**

Keep that flag unset or set to `"0"` in production.

</div>

For full configuration reference and troubleshooting, see [mTLS Federation Transport](../security/mtls.md).

## Step 3 — Rotate the Ed25519 identity key

The node identity key signs federation manifests and peer tokens. `Spec-10-Hardening` requires rotation at least every 365 days; shorter is better.

```bash
# Dry run first — confirms TL connectivity and shows new key_id without committing
docker compose exec stigmem-node \
  stigmem identity rotate-key --kind node --dry-run
```

If the dry run reports a transparency-log error, check that the TL backend is reachable before proceeding.

```bash
# Commit the rotation
docker compose exec stigmem-node \
  stigmem identity rotate-key --kind node
```

Output:

```
Key rotation (node) complete
old key_id : a1b2c3d4e5f60001
new key_id : 9f8e7d6c5b4a0002
dual-trust : 2026-08-02T12:00:00Z
manifest TL index  : 43
rotation TL index  : 44

ACTION REQUIRED — update your secrets manager with the new private key:
  STIGMEM_NODE_PRIVATE_KEY=<base64url seed>
```

**Update the secret and restart:**

```bash
sed -i 's|^STIGMEM_NODE_PRIVATE_KEY=.*|STIGMEM_NODE_PRIVATE_KEY=<new-seed>|' .env
docker compose up -d
```

**Verify the new key is live:**

```bash
curl -s https://your-node.example.com/.well-known/stigmem-manifest.json | jq .key_id
# → "9f8e7d6c5b4a0002"
```

Record the `dual-trust` expiry date in your key rotation log. The retiring key remains in the accept-set until that date.

## Step 4 — Rotate the capability issuer key

Capability tokens are signed by a separate issuer key. Rotate it at least every 90 days.

```bash
docker compose exec stigmem-node \
  stigmem identity rotate-key --kind issuer
```

<div className="stigmem-keypoint">

**The dual-trust window for the issuer key must be ≥ 90 days.**

This is the maximum capability token TTL per
`Spec-06-Capability-Tokens`. The CLI enforces this minimum.

</div>

Update the `STIGMEM_ISSUER_PRIVATE_KEY` secret and restart the node the same way as Step 3.

**Post-rotation checklist** (both keys):

<div className="stigmem-grid">

<div><h4>Manifest reflects new key</h4><p>Visible at <code>/.well-known/stigmem-manifest.json</code>.</p></div>
<div><h4>Node restarted</h4><p><code>/healthz</code> returns 200.</p></div>
<div><h4>Capability tokens verify</h4><p>With <code>stigmem capability verify</code>.</p></div>
<div><h4>Retiring key archived</h4><p>Read-only secrets until <code>dual_trust_expires_at</code>.</p></div>

</div>

For the full security model and threat notes, see [Key Rotation Runbook](../security/key-rotation.md).

## Step 5 — Tune quotas and verify 429 behaviour

The default quota ceilings (1 000 writes/hour, 5 000 reads/hour) protect shared nodes from noisy neighbours. After 24 hours of representative traffic, review `quota_breach` audit events and adjust.

**Check current breach rate:**

```bash
# Requires an audit.read key (Step 6 sets this up — run Step 6 first if needed)
curl -s "http://localhost:8000/v1/admin/audit?event_type=quota_breach&limit=100" \
  -H "Authorization: Bearer $AUDIT_KEY" \
  | jq '[.entries[] | .entity_uri] | group_by(.) | map({principal: .[0], count: length}) | sort_by(-.count)'
```

**Increase ceilings for a high-ingest node:**

```bash
# In your environment / Compose override
STIGMEM_RATE_LIMIT_WRITE_PER_HOUR=10000
STIGMEM_RATE_LIMIT_READ_PER_HOUR=50000
```

Restart the node.

<div className="stigmem-keypoint">

**Do not set both quota knobs to `0` in production.**

That kill switch disables quota enforcement globally. Stigmem logs a
startup `SECURITY WARNING` when it is active; it is intended only
for isolated local/dev/test environments.

</div>

**Verify 429 enforcement:**

```bash
# Write 200 facts in a tight loop to a fresh key; expect 429s after the bucket empties
API_KEY="<a key with write scope>"
for i in $(seq 1 200); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" \
    -X POST http://localhost:8000/v1/facts \
    -H "Authorization: Bearer $API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"entity\":\"stigmem://test/e${i}\",\"relation\":\"seq\",\"value\":\"${i}\",\"scope\":\"team\"}")
  [[ "$STATUS" == "429" ]] && echo "429 at write ${i}" && break
done
```

A 429 confirms the token-bucket quota is active:

```json
{
  "error": "quota_exceeded",
  "dimension": "fact_write",
  "principal": "stigmem://your-org.example.com/agent",
  "retry_after": 3.2
}
```

For the full quota model and Prometheus metrics, see [Audit Log & Per-Principal Quotas](../security/audit-and-quotas.md#per-principal-quotas).

## Step 6 — Mint an audit key and confirm events

```bash
AUDIT_KEY=$(curl -s -X POST http://localhost:8000/v1/admin/api-keys \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_uri":"stigmem://your-org.example.com/siem-reader","permissions":["audit.read"]}' \
  | jq -r '.key')

echo "Audit key: $AUDIT_KEY"
```

Trigger a few events, then verify they appear:

```bash
curl -s "http://localhost:8000/v1/admin/audit?limit=10" \
  -H "Authorization: Bearer $AUDIT_KEY" \
  | jq '.entries[] | {seq, event_type, ts}'
```

You should see `fact_write` events (for the assertions in Step 5), and `quota_breach` if you hit the 429 limit.

**Verify that a non-audit key is rejected:**

```bash
curl -s http://localhost:8000/v1/admin/audit \
  -H "Authorization: Bearer $API_KEY" \
  | jq .
# → {"detail": "audit.read capability required"}
```

Store `AUDIT_KEY` in your secrets manager and configure your SIEM to poll `/v1/admin/audit` on a schedule.

## Step 7 — Switch to the hardened container image

<div className="stigmem-keypoint">

**The v0.9.0a6 reference image runs as UID/GID 65532 (non-root).**

Distroless base, read-only root filesystem, and a custom seccomp profile.

</div>

**Pull and verify the image:**

```bash
docker pull ghcr.io/eidetic-labs/stigmem-node:0.9.0a6

# Verify the Sigstore keyless signature
cosign verify \
  --certificate-identity-regexp "https://github.com/eidetic-labs/stigmem/.github/workflows/publish.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/eidetic-labs/stigmem-node:0.9.0a6
```

**Run with the full security posture:**

```bash
docker run -d \
  --user 65532:65532 \
  --read-only \
  --tmpfs /tmp:mode=1777,size=64m \
  --tmpfs /run:mode=755,size=16m \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --security-opt seccomp=deploy/seccomp/stigmem-node.json \
  -v stigmem-data:/data \
  -e STIGMEM_DB_PATH=/data/stigmem.db \
  -e STIGMEM_TLS_CERT_PATH=/tls/node.crt \
  -e STIGMEM_TLS_KEY_PATH=/tls/node.key \
  -e STIGMEM_TLS_CA_BUNDLE=/tls/ca.crt \
  -v /etc/stigmem/tls:/tls:ro \
  -p 8765:8765 \
  ghcr.io/eidetic-labs/stigmem-node:0.9.0a6
```

**Verify the process runs as non-root:**

```bash
docker exec $(docker ps -qf name=stigmem-node) id
# → uid=65532(nonroot) gid=65532(nonroot)
```

**Verify the read-only filesystem:**

```bash
docker exec $(docker ps -qf name=stigmem-node) \
  touch /etc/test 2>&1 | grep -i "read-only"
# → touch: /etc/test: Read-only file system
```

For Kubernetes / Helm security context configuration and SBOM verification, see [Container Hardening](../security/container-hardening.md).

## Step 8 — Preserve immutable evidence

The ADR-016 storage-immutability stack gives clients and peers tamper evidence through CIDs, local fact-chain verification, and transparency-log checkpoints. Operators still need to preserve that evidence outside the mutable node.

For production:

<div className="stigmem-grid">

<div><h4>External fact-chain</h4><p>Use <code>STIGMEM_TL_BACKEND=rekor</code> for external checkpoints where possible.</p></div>
<div><h4>Local TL hardening</h4><p>If using <code>STIGMEM_TL_BACKEND=local</code>, place <code>STIGMEM_TL_LOCAL_PATH</code> on storage the node process cannot rewrite outside append-only operation.</p></div>
<div><h4>WORM export</h4><p>Export <code>fact_audit_log</code> and <code>federation_audit</code> rows to WORM-capable object storage before local retention expiry.</p></div>
<div><h4>Snapshot retention</h4><p>Keep signed database snapshots under retention lock, with Rekor checkpoint metadata.</p></div>
<div><h4>TEE evaluation</h4><p>For high-assurance deployments, evaluate a TEE-capable runtime and seal node private keys to the measured runtime.</p></div>

</div>

See [Immutability & Attestation](../security/immutability-and-attestation.md) for the R-23 mitigation stack, verification commands, WORM storage guidance, and TEE deployment notes.

## Final verification

```bash
# 1. mTLS active
openssl s_client -connect localhost:8765 \
  -cert /etc/stigmem/tls/node.crt -key /etc/stigmem/tls/node.key \
  -CAfile /etc/stigmem/tls/ca.crt 2>/dev/null | grep "Verify return code: 0"

# 2. Key rotation recorded in manifest
curl -s https://your-node.example.com/.well-known/stigmem-manifest.json \
  | jq '.rotation_events | length'
# → 1 or more

# 3. Quota enforcement active (expect 429 in earlier traffic)
curl -s "http://localhost:8000/v1/admin/audit?event_type=quota_breach&limit=1" \
  -H "Authorization: Bearer $AUDIT_KEY" | jq '.total'

# 4. Non-root container
docker exec $(docker ps -qf name=stigmem-node) id | grep 65532

# 5. Healthcheck passing
curl -s https://your-node.example.com/healthz | jq .status
# → "ok"

# 6. Full verification metadata available
curl -s https://your-node.example.com/v1/recall \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Stigmem-Verify: full" \
  -H "Content-Type: application/json" \
  -d '{"query":"hardening check","scope":"company","token_budget":1000}' \
  | jq '.chain_proof'
```

## What you have now

<div className="stigmem-fields">

<div>
<dt>Control</dt>
<dt><span className="stigmem-fields__type">Spec / ADR</span></dt>
<dd>Status</dd>
</div>

<div>
<dt>mTLS federation with SAN validation</dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>Ed25519 identity key rotated with dual-trust</dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>Capability issuer key rotated</dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>Audit log with 14 event types</dt>
<dt><span className="stigmem-fields__type">Spec-09</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>Per-principal token-bucket quotas</dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>Non-root distroless, read-only fs, dropped caps</dt>
<dt><span className="stigmem-fields__type">Spec-10</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>CID + hash-chain + checkpoint verification plan</dt>
<dt><span className="stigmem-fields__type">ADR-016</span></dt>
<dd>Active</dd>
</div>

<div>
<dt>WORM/TEE evidence plan</dt>
<dt><span className="stigmem-fields__type">ADR-016</span></dt>
<dd>Deployment option</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Your deployment is now at the pre-reset hardening hardened posture.**

Run the [Community Pen-Test Handbook](../security/pen-test.md) test
matrix against it to verify from the attacker's perspective.

</div>

## Next steps

<div className="stigmem-grid">

<div><h4>Rotation reminders</h4><p>Issuer key every 90 days, identity key every 365 days.</p></div>
<div><h4>SIEM retention</h4><p>Export <code>fact_audit_log</code> rows to immutable storage before the 90-day minimum window.</p></div>
<div><h4>Post-rotation checklist</h4><p>Review the <a href="../security/key-rotation.md#rotation-checklist">Key Rotation Runbook</a>.</p></div>
<div><h4>Auto-rotation</h4><p>For cert-manager on Kubernetes, see <a href="../security/mtls.md#cert-manager-kubernetes">mTLS — cert-manager</a>.</p></div>
<div><h4>Immutability review</h4><p>Review <a href="../security/immutability-and-attestation.md">Immutability &amp; Attestation</a> before enabling production federation.</p></div>

</div>
