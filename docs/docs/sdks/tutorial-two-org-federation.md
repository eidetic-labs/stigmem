---
title: "Tutorial: Two-Org Federated Network"
sidebar_label: Two-Org Federated Network
description: End-to-end walkthrough — two Stigmem nodes with distinct Ed25519 identities, org manifests, capability tokens, a quarantine review cycle, and a verified provenance chain.
audience: Integrator
---

# Tutorial: Two-Org Federated Network

**Audience:** node operators and protocol implementers setting up cross-org federation for the first time.
**Spec references:** §6 Federation, §19 Federation Trust (canonicalized at v0.9.0a1; see [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)), §5.21–5.25 wire format.
**Time:** ~30 minutes on two local machines or two cloud VMs. A laptop with two terminal windows works fine.

---

This tutorial walks through a complete two-organisation Stigmem federation: two nodes, separate Ed25519 identities, mutual org manifests, a capability token granting Org B write access to a shared scope on Org A, a quarantine review cycle, and an end-to-end provenance chain verification.

By the end you will have:

- Two running Stigmem nodes that replicate facts between each other.
- Org A issuing a time-limited capability token to Org B.
- A fact written by Org B that lands in Org A's quarantine garden (because Org B is a new, low-trust source) and is then admitted by an Org A moderator.
- A provenance chain on the admitted fact that you can verify with a single `curl`.

---

## Prerequisites

- Python 3.11+ with `pip`
- `openssl` (standard on macOS/Linux)
- `curl` (standard) and `jq` (for pretty-printing responses)
- Two terminal windows (or two machines / cloud VMs). This tutorial calls them **Terminal A** and **Terminal B**.

Install the node with the `libsql` extra disabled (we use the default SQLite backend for local testing):

```bash
pip install 'stigmem-node'
```

Check the installed version:

```bash
stigmem --version
# stigmem-node 1.1.x
```

---

## Step 1 — Bootstrap node identities

Each node needs an Ed25519 keypair. This keypair signs org manifests, capability tokens, and snapshots — it is the cryptographic root of the node's identity.

### Terminal A — Org A

```bash
mkdir -p ~/stigmem-org-a && cd ~/stigmem-org-a

# Generate Org A's signing keypair
openssl genpkey -algorithm Ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out signing.pub

# Derive base64url public key and SHA-256 key_id
export ORG_A_PUB=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | base64 | tr '+/' '-_' | tr -d '=')
export ORG_A_KEY_ID=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | sha256sum | awk '{print $1}')

echo "Org A public key : $ORG_A_PUB"
echo "Org A key_id     : $ORG_A_KEY_ID"
```

### Terminal B — Org B

```bash
mkdir -p ~/stigmem-org-b && cd ~/stigmem-org-b

openssl genpkey -algorithm Ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out signing.pub

export ORG_B_PUB=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | base64 | tr '+/' '-_' | tr -d '=')
export ORG_B_KEY_ID=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | sha256sum | awk '{print $1}')

echo "Org B public key : $ORG_B_PUB"
echo "Org B key_id     : $ORG_B_KEY_ID"
```

---

## Step 2 — Start both nodes

### Terminal A

```bash
cd ~/stigmem-org-a

STIGMEM_NODE_PRIVATE_KEY_FILE=signing.key \
STIGMEM_ENTITY_URI=stigmem://org-a.example \
STIGMEM_PORT=8100 \
STIGMEM_FEDERATION_ENABLED=true \
STIGMEM_TRUST_MODE=strict \
STIGMEM_ADMIN_KEY=secret-admin-a \
  stigmem serve &

# Confirm the node is up
curl -s http://localhost:8100/.well-known/stigmem | jq .
```

Expected (abbreviated):

```json
{
  "version": "1.0",
  "node_id": "stigmem:node:<uuid>",
  "federation": "enabled",
  "federation_trust": { "trust_mode": "strict" }
}
```

### Terminal B

```bash
cd ~/stigmem-org-b

STIGMEM_NODE_PRIVATE_KEY_FILE=signing.key \
STIGMEM_ENTITY_URI=stigmem://org-b.example \
STIGMEM_PORT=8200 \
STIGMEM_FEDERATION_ENABLED=true \
STIGMEM_TRUST_MODE=strict \
STIGMEM_ADMIN_KEY=secret-admin-b \
  stigmem serve &

curl -s http://localhost:8200/.well-known/stigmem | jq .
```

---

## Step 3 — Publish org manifests

Each node must publish a signed manifest that declares its public key and the entity URIs it is authoritative for (§19.1).

### Terminal A — Publish Org A manifest

```bash
# Build the manifest JSON
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EXPIRES=$(date -u -d '+1 year' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
          || date -u -v+1y +%Y-%m-%dT%H:%M:%SZ)

# The manifest body (everything except "signature") must be JCS-canonical JSON.
# For this tutorial we use the node's built-in helper to sign and publish in one step.
curl -s -X PUT http://localhost:8100/v1/federation/manifest \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{
    \"manifest_version\": 1,
    \"entity_uri\":  \"stigmem://org-a.example\",
    \"public_key\":  \"$ORG_A_PUB\",
    \"key_id\":      \"$ORG_A_KEY_ID\",
    \"entities\":    [\"stigmem://org-a.example\", \"stigmem://org-a.example/agent/assistant\"],
    \"rotation_events\": [],
    \"issued_at\":   \"$NOW\",
    \"expires_at\":  \"$EXPIRES\",
    \"signature\":   \"__self_sign__\"
  }" | jq .
```

:::note `__self_sign__`
The reference node accepts the literal `__self_sign__` for the `signature` field when `STIGMEM_NODE_PRIVATE_KEY_FILE` is configured. The node computes the JCS-canonical signature internally. For production deployments, compute the signature externally (see the [Federation Trust guide](../concepts/federation/federation-trust.md)).
:::

Expected response:

```json
{
  "entity_uri": "stigmem://org-a.example",
  "key_id": "...",
  "issued_at": "2026-05-04T...",
  "log_entry": {
    "log_id": "local-tl",
    "log_index": 1,
    "leaf_hash": "sha256:..."
  }
}
```

### Terminal B — Publish Org B manifest

```bash
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EXPIRES=$(date -u -d '+1 year' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
          || date -u -v+1y +%Y-%m-%dT%H:%M:%SZ)

curl -s -X PUT http://localhost:8200/v1/federation/manifest \
  -H "Authorization: Bearer secret-admin-b" \
  -H "Content-Type: application/json" \
  -d "{
    \"manifest_version\": 1,
    \"entity_uri\":  \"stigmem://org-b.example\",
    \"public_key\":  \"$ORG_B_PUB\",
    \"key_id\":      \"$ORG_B_KEY_ID\",
    \"entities\":    [\"stigmem://org-b.example\", \"stigmem://org-b.example/agent/bot\"],
    \"rotation_events\": [],
    \"issued_at\":   \"$NOW\",
    \"expires_at\":  \"$EXPIRES\",
    \"signature\":   \"__self_sign__\"
  }" | jq .
```

### Register as federation peers

Register each node with the other so they can pull facts (§6.2):

```bash
# Terminal A: tell Org A about Org B
curl -s -X POST http://localhost:8100/v1/federation/peers \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_url": "http://localhost:8200",
    "peer_entity_uri": "stigmem://org-b.example"
  }' | jq .

# Terminal B: tell Org B about Org A
curl -s -X POST http://localhost:8200/v1/federation/peers \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_url": "http://localhost:8100",
    "peer_entity_uri": "stigmem://org-a.example"
  }' | jq .
```

### Verify Rekor inclusion (optional)

If your node is configured with a live Rekor endpoint (`STIGMEM_REKOR_URL`), the `log_entry` in the manifest response will include a Merkle-tree proof URL. Verify it with:

```bash
rekor-cli verify \
  --rekor_server https://rekor.sigstore.dev \
  --entry <log_index_from_response>
```

For this local tutorial, the node uses a built-in local transparency log stub. Rekor integration is described in the [Federation Trust guide — Transparency Log section](../concepts/federation/federation-trust.md).

---

## Step 4 — Configure peer trust and create a quarantine garden

With `STIGMEM_TRUST_MODE=strict`, Org A will quarantine facts from Org B until Org B holds a valid capability token for the target scope. First, create the quarantine garden on Org A:

```bash
# Terminal A — create the quarantine garden
QUARANTINE_ID=$(curl -s -X POST http://localhost:8100/v1/gardens \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{
    "slug":        "inbound-quarantine",
    "name":        "Inbound quarantine",
    "scope":       "company",
    "quarantine":  true
  }' | jq -r '.id')

echo "Quarantine garden ID: $QUARANTINE_ID"

# Designate it as the node-level quarantine sink
curl -s -X PATCH http://localhost:8100/v1/admin/config \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{\"quarantine_garden_id\": \"$QUARANTINE_ID\"}" | jq .
```

---

## Step 5 — Issue a capability token from Org A to Org B

Org A issues a 24-hour capability token granting Org B's agent write access to the `stigmem://org-a.example/scope/shared` scope (§19.3, §5.23):

```bash
# Terminal A — issue the token
TOKEN_RESPONSE=$(curl -s -X POST http://localhost:8100/v1/federation/capability-tokens \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{
    "issuer":      "stigmem://org-a.example",
    "subject":     "stigmem://org-b.example/agent/bot",
    "verb":        "write",
    "object":      "stigmem://org-a.example/scope/shared",
    "ttl_seconds": 86400
  }')

echo "$TOKEN_RESPONSE" | jq .

TOKEN_ID=$(echo "$TOKEN_RESPONSE" | jq -r '.token_id')
TOKEN_JSON=$(echo "$TOKEN_RESPONSE" | jq -r '.token_json')

echo "Token ID  : $TOKEN_ID"
```

### Verify the token from Org B's perspective

Copy `$TOKEN_JSON` to Terminal B and verify it is valid:

```bash
# Terminal B — verify the token issued by Org A
curl -s -X POST http://localhost:8100/v1/federation/capability-tokens/verify \
  -H "Content-Type: application/json" \
  -d "{\"token_json\": $TOKEN_JSON}" | jq .
# → { "valid": true }
```

The six-step verification (§19.3.3) checks token version, expiry, issuer manifest, signature, subject delegation, and revocation status.

---

## Step 6 — Write a fact from Org B; observe quarantine

Org B writes a fact to Org A using the capability token. Because Org B is a new peer with no `peer_history` score yet, its source-trust score `t` will be below the `strict` mode quarantine threshold (0.2), so the fact lands in the quarantine garden before entering the main fact store.

```bash
# Terminal B — write a fact to Org A using the capability token
curl -s -X POST http://localhost:8100/v1/facts \
  -H "Authorization: Bearer $TOKEN_JSON" \
  -H "Content-Type: application/json" \
  -d '{
    "entity":     "stigmem://org-a.example/project/atlas",
    "relation":   "memory:status",
    "value":      { "type": "string", "v": "active" },
    "source":     "stigmem://org-b.example/agent/bot",
    "confidence": 0.85,
    "scope":      "company"
  }' | jq .
```

Expected response:

```json
{
  "fact_id": "<uuid>",
  "quarantine_status": "pending",
  "quarantine_garden_id": "<quarantine-garden-uuid>",
  "quarantine_reason": "auto-quarantine: source_trust below threshold (t=0.15)"
}
```

The fact is stored but isolated — it will not appear in normal `GET /v1/facts` queries until a moderator admits it.

### Confirm the fact is in quarantine

```bash
# Terminal A — list pending quarantine items
curl -s "http://localhost:8100/v1/quarantine?quarantine_status=pending" \
  -H "Authorization: Bearer secret-admin-a" | jq .
```

You should see the fact from Org B with `quarantine_status: "pending"`.

---

## Step 7 — Admit the fact through the quarantine garden

An Org A moderator reviews the quarantined fact and promotes it to the main fact store:

```bash
# Terminal A — promote the quarantined fact
FACT_ID="<fact_id from the write response>"

curl -s -X POST "http://localhost:8100/v1/gardens/$QUARANTINE_ID/promote" \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{
    \"fact_id\":          \"$FACT_ID\",
    \"target_garden_id\": null,
    \"reason\":           \"Org B status update verified; source has valid capability token.\"
  }" | jq .
```

Expected response:

```json
{
  "fact_id": "<uuid>",
  "action":  "promoted",
  "target_garden_id": null,
  "acted_by": "user:admin",
  "acted_at": "2026-05-04T..."
}
```

`target_garden_id: null` promotes the fact to the main fact store (outside any garden boundary). To promote into a specific garden instead, pass the garden UUID.

To **reject** the fact (sets `confidence = 0`, retains for audit):

```bash
curl -s -X POST "http://localhost:8100/v1/gardens/$QUARANTINE_ID/reject" \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{\"fact_id\": \"$FACT_ID\", \"reason\": \"Source unverified.\"}" | jq .
```

---

## Step 8 — Verify the provenance chain end-to-end

After promotion, the fact's provenance chain captures its journey: written by Org B, admitted by Org A's moderator. Verify it:

```bash
# Terminal A — retrieve the admitted fact and inspect provenance
curl -s "http://localhost:8100/v1/facts/$FACT_ID" \
  -H "Authorization: Bearer secret-admin-a" | jq '{
    fact_id:          .id,
    entity:           .entity,
    relation:         .relation,
    value:            .value,
    source:           .source,
    source_trust:     .source_trust,
    derived_from:     .derived_from,
    attestation_chain: .attestation_chain,
    quarantine_status: .quarantine_status
  }'
```

Expected (abbreviated):

```json
{
  "fact_id":           "<uuid>",
  "entity":            "stigmem://org-a.example/project/atlas",
  "relation":          "memory:status",
  "value":             { "type": "string", "v": "active" },
  "source":            "stigmem://org-b.example/agent/bot",
  "source_trust":      0.15,
  "derived_from":      [],
  "attestation_chain": ["<base64url Ed25519 sig by org-b.example>"],
  "quarantine_status": "promoted"
}
```

The `attestation_chain` contains Org B's Ed25519 signature over the fact body (§19.6). The `source_trust` snapshot records the trust score at write time; effective confidence at recall time uses the live recomputed score.

### Full chain hash verification

```bash
# Recompute the fact hash and verify against the stored derived_from or attestation chain
python3 - <<'EOF'
import json, hashlib, canonicaljson

fact = {
  "entity":     "stigmem://org-a.example/project/atlas",
  "relation":   "memory:status",
  "value":      {"type": "string", "v": "active"},
  "scope":      "company",
  "source":     "stigmem://org-b.example/agent/bot",
  "confidence": 0.85,
  "ts":         "<ts-from-fact-response>"
}

canonical = canonicaljson.encode_canonical_json(fact)
fact_hash = hashlib.sha256(canonical).hexdigest()
print(f"Fact hash: {fact_hash}")
EOF
```

---

## Step 9 — Revoke the capability token (cleanup)

When the collaboration ends or the token is no longer needed, revoke it. Revocations are written to the transparency log and propagated to peers within the TTL cache window (§19.3.4):

```bash
# Terminal A — revoke the token
curl -s -X POST "http://localhost:8100/v1/federation/capability-tokens/$TOKEN_ID/revoke" \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Tutorial complete; token no longer needed."}' | jq .
```

After revocation, a fresh verify call returns `{"valid": false, "reason": "revoked"}`.

---

## What you built

You now have a working two-org federated Stigmem network with:

| Capability | How it works |
|---|---|
| Distinct node identities | Each node has an Ed25519 keypair; manifests anchor the key to an org URI |
| Org manifests + transparency log | Manifests published via `PUT /v1/federation/manifest`; inclusion proof returned and stored |
| Peer trust | Peers registered via `POST /v1/federation/peers`; federation pulls scoped facts using signed peer tokens |
| Capability token | Org A issued a 24 h `write` token to Org B; Org B presented it on every write |
| Quarantine path | Org B's first write landed in the quarantine garden (source trust below threshold) |
| Moderator admission | Org A's admin promoted the quarantined fact to the main store |
| Provenance chain | Promoted fact carries Org B's attestation signature; verifiable at any time |
| Token revocation | Token revoked; subsequent verify calls return `valid: false` |

---

## Next steps

- **4-node topology:** see the [4-Node Federation guide](../concepts/federation/federation-4node.md) for N-node backpressure, relay configuration, and scope propagation invariants (§6.7–6.8).
- **Key rotation:** rotate Org A's signing key without federation downtime — see the Key Rotation section in the [Federation Trust guide](../concepts/federation/federation-trust.md).
- **Trust mode tuning:** lower `STIGMEM_QUARANTINE_TRUST_THRESHOLD` to admit more facts automatically from known peers.
- **Encrypted storage:** add `STIGMEM_AT_REST_ENCRYPTION=on` before going to production — [Backends guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/storage-backends).
- **Signed snapshots:** back up both nodes — [Backends guide](https://github.com/Eidetic-Labs/stigmem/tree/main/experimental/storage-backends).
