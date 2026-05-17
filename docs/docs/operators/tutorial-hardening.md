---
title: "Tutorial: Harden a Stigmem Deployment"
sidebar_label: Harden a Deployment
description: Walk an operator from a default Stigmem node to a pre-reset hardening–hardened deployment — mTLS, key rotation, per-principal quotas, and a distroless container — end to end.
audience: Integrator
---

# Tutorial: Harden a Stigmem Deployment

**Audience:** node operators running Stigmem in production or preparing for production.  
**Time:** ~45 minutes.  
**Outcome:** a running Stigmem node with mTLS federation, rotated Ed25519 identity and issuer keys, per-principal quotas tuned to your baseline traffic, the hardened distroless container image, and an operator plan for immutable evidence.

**Prerequisites:**
- A Stigmem node running the v0.9.0a1 reference image (`ghcr.io/eidetic-labs/stigmem-node:0.9.0a1`). For hardened production, pin to a digest (`@sha256:<digest>`) instead — see the [tag-selection guide](./deployment/install#image-tags).
- Docker Compose installed (`docker compose version`).
- `openssl`, `curl`, `jq` available.
- Admin API key (`STIGMEM_ADMIN_KEY`).

All commands run against a local Docker Compose node.  Adapt `https://your-node.example.com` substitutions for a remote deployment.

---

## What you will do

```
Step 1 — mTLS: generate a federation CA and issue a node cert
Step 2 — mTLS: configure the node and verify mutual TLS
Step 3 — Key rotation: rotate the Ed25519 identity key
Step 4 — Key rotation: rotate the capability issuer key
Step 5 — Quotas: tune write/read ceilings and verify 429 behaviour
Step 6 — Audit: mint an audit.read key and confirm events are emitted
Step 7 — Container: switch to the hardened image and verify seccomp
Step 8 — Immutability: route evidence to WORM storage and plan TEE deployment
```

---

## Step 1 — Generate a federation CA and node cert

Start with a self-managed CA (suitable for small clusters and test environments).  For larger clusters, replace this step with a cert-manager `ClusterIssuer` — see [mTLS Federation Transport](../security/mtls.md#cert-manager-kubernetes).

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

---

## Step 2 — Configure mTLS and verify

Add the three TLS environment variables to your Compose override or node environment, then restart:

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

You should see the node cert fingerprint and `CN=stigmem-node`.

**Verify that a plaintext connection is rejected:**

```bash
curl http://localhost:8765/healthz 2>&1 | grep -i "empty reply\|SSL\|refused"
# Expect: connection refused or SSL handshake error — not an HTTP 200
```

> If you see an HTTP response here, TLS is not yet active — check that `STIGMEM_TLS_CERT_PATH` and `STIGMEM_TLS_KEY_PATH` are set and the files are readable.

Federation will not start without those TLS settings unless
`STIGMEM_FEDERATION_INSECURE=1` is explicitly set. Keep that flag unset or set
to `"0"` in production.

For full configuration reference and troubleshooting, see [mTLS Federation Transport](../security/mtls.md).

---

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
# Docker Compose — update the env file, then restart
sed -i 's|^STIGMEM_NODE_PRIVATE_KEY=.*|STIGMEM_NODE_PRIVATE_KEY=<new-seed>|' .env
docker compose up -d
```

**Verify the new key is live:**

```bash
curl -s https://your-node.example.com/.well-known/stigmem-manifest.json | jq .key_id
# → "9f8e7d6c5b4a0002"
```

Record the `dual-trust` expiry date in your key rotation log.  The retiring key remains in the accept-set until that date.

---

## Step 4 — Rotate the capability issuer key

Capability tokens are signed by a separate issuer key (`Spec-10-Hardening`). Rotate it at least every 90 days.

```bash
docker compose exec stigmem-node \
  stigmem identity rotate-key --kind issuer
```

The dual-trust window for the issuer key must be >= 90 days (the maximum capability token TTL per `Spec-06-Capability-Tokens`). The CLI enforces this minimum.

Update the `STIGMEM_ISSUER_PRIVATE_KEY` secret and restart the node the same way as Step 3.

**Post-rotation checklist** (both keys):

- [ ] New key visible at `/.well-known/stigmem-manifest.json`
- [ ] Node restarted and `/healthz` returns 200
- [ ] Existing capability tokens verified with `stigmem capability verify`
- [ ] Retiring key archived in read-only secrets until `dual_trust_expires_at`

For the full security model and threat notes, see [Key Rotation Runbook](../security/key-rotation.md).

---

## Step 5 — Tune quotas and verify 429 behaviour

The default quota ceilings (1 000 writes/hour, 5 000 reads/hour) protect shared nodes from noisy neighbours.  After 24 hours of representative traffic, review `quota_breach` audit events and adjust.

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

Do not set both quota knobs to `0` in production. That kill switch disables
quota enforcement globally and Stigmem logs a startup `SECURITY WARNING` when
it is active; it is intended only for isolated local/dev/test environments.

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

A 429 confirms the token-bucket quota is active.  The response body includes `retry_after` seconds and the dimension name:

```json
{
  "error": "quota_exceeded",
  "dimension": "fact_write",
  "principal": "stigmem://your-org.example.com/agent",
  "retry_after": 3.2
}
```

For the full quota model and Prometheus metrics, see [Audit Log & Per-Principal Quotas](../security/audit-and-quotas.md#per-principal-quotas).

---

## Step 6 — Mint an audit key and confirm events

```bash
AUDIT_KEY=$(curl -s -X POST http://localhost:8000/v1/admin/api-keys \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entity_uri":"stigmem://your-org.example.com/siem-reader","permissions":["audit.read"]}' \
  | jq -r '.key')

echo "Audit key: $AUDIT_KEY"
```

Trigger a few events (assert a fact, exceed a quota limit), then verify they appear:

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

---

## Step 7 — Switch to the hardened container image

The v0.9.0a1 reference image runs as UID/GID 65532 (non-root) on a distroless base with a read-only root filesystem and a custom seccomp profile.

**Pull and verify the image:**

```bash
docker pull ghcr.io/eidetic-labs/stigmem-node:0.9.0a1

# Verify the Sigstore keyless signature
cosign verify \
  --certificate-identity-regexp "https://github.com/Eidetic-Labs/stigmem/.github/workflows/publish.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
  ghcr.io/eidetic-labs/stigmem-node:0.9.0a1
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
  ghcr.io/eidetic-labs/stigmem-node:0.9.0a1
```

Or use the deploy Compose recipe, which applies the same flags automatically:

```bash
docker compose -f deploy/compose/docker-compose.yml up -d
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

---

## Step 8 — Preserve immutable evidence

The ADR-016 storage-immutability stack gives clients and peers tamper evidence through CIDs, local fact-chain verification, and transparency-log checkpoints. Operators still need to preserve that evidence outside the mutable node.

For production:

- Use `STIGMEM_TL_BACKEND=rekor` for external fact-chain checkpoints where possible.
- If using `STIGMEM_TL_BACKEND=local`, place `STIGMEM_TL_LOCAL_PATH` on storage the node process cannot rewrite outside append-only operation.
- Export `fact_audit_log` and `federation_audit` rows to WORM-capable object storage before local retention expiry.
- Keep signed database snapshots under retention lock, and record Rekor checkpoint metadata with restore evidence.
- For high-assurance deployments, evaluate a TEE-capable runtime and seal node private keys to the measured runtime.

See [Immutability & Attestation](../security/immutability-and-attestation.md) for the R-23 mitigation stack, verification commands, WORM storage guidance, and TEE deployment notes.

---

## Final verification

Run the full hardening checklist:

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

---

## What you have now

| Control | Spec | Status |
|---|---|---|
| mTLS federation with SAN validation | `Spec-10-Hardening` | Active |
| Ed25519 identity key rotated with dual-trust window | `Spec-10-Hardening` | Active |
| Capability issuer key rotated | `Spec-10-Hardening` | Active |
| Audit log with 14 event types | `Spec-09-Audit-Log` | Active |
| Per-principal token-bucket quotas | `Spec-10-Hardening` | Active |
| Non-root distroless container, read-only fs, dropped caps | `Spec-10-Hardening` | Active |
| CID, local hash-chain, and checkpoint verification plan | `ADR-016` | Active |
| WORM/TEE evidence plan | `ADR-016` | Deployment option |

Your deployment is now at the pre-reset hardening hardened posture.  Run the [Community Pen-Test Handbook](../security/pen-test.md) test matrix against it to verify from the attacker's perspective.

---

## Next steps

- Schedule key rotation reminders: issuer key every 90 days, identity key every 365 days.
- Configure SIEM retention — export `fact_audit_log` rows to immutable storage before the 90-day minimum window.
- Review the [Key Rotation Runbook](../security/key-rotation.md#rotation-checklist) post-rotation checklist.
- For cert-manager-based auto-rotation on Kubernetes, see [mTLS — cert-manager](../security/mtls.md#cert-manager-kubernetes).
- Review [Immutability & Attestation](../security/immutability-and-attestation.md) before enabling production federation.
