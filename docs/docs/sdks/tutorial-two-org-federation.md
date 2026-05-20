---
title: "Tutorial: Two-Org Federated Network"
sidebar_label: Two-Org Federated Network
description: End-to-end walkthrough — two Stigmem nodes with distinct Ed25519 identities, org manifests, capability tokens, a quarantine review cycle, and a verified provenance chain.
audience: Integrator
---

# Tutorial: Two-Org Federated Network

<p className="stigmem-meta"><span>30 min · tutorial</span><span>Node operator · Implementer</span><span>End-to-end</span></p>

<div className="stigmem-lead">

**What you will build**

A complete two-organisation Stigmem federation: two nodes, separate
Ed25519 identities, mutual org manifests, a capability token
granting Org B write access to a shared scope on Org A, a
quarantine review cycle, and an end-to-end provenance chain
verification.

</div>

**Audience:** node operators and protocol implementers setting up cross-org federation for the first time.
**Spec references:** §6 Federation, §19 Federation Trust, §5.21–5.25 wire format.
**Time:** ~30 minutes on two local machines or two cloud VMs.

**By the end you will have:**

<div className="stigmem-grid">

<div><h4>Two running nodes</h4><p>That replicate facts between each other.</p></div>
<div><h4>Capability token</h4><p>Org A issuing a time-limited capability token to Org B.</p></div>
<div><h4>Quarantine cycle</h4><p>A fact written by Org B lands in Org A's quarantine garden (low source-trust) and is then admitted by an Org A moderator.</p></div>
<div><h4>Verifiable provenance</h4><p>A provenance chain on the admitted fact that you can verify with a single <code>curl</code>.</p></div>

</div>

## Prerequisites

<div className="stigmem-grid">

<div><h4>Python 3.11+</h4><p>With <code>pip</code>.</p></div>
<div><h4><code>openssl</code></h4><p>Standard on macOS/Linux.</p></div>
<div><h4><code>curl</code> + <code>jq</code></h4><p><code>jq</code> for pretty-printing responses.</p></div>
<div><h4>Two terminals</h4><p>Called <strong>Terminal A</strong> and <strong>Terminal B</strong>.</p></div>

</div>

```bash
pip install 'stigmem-node'
stigmem --version
# stigmem-node 1.1.x
```

## Step 1 — Bootstrap node identities

<div className="stigmem-keypoint">

**Each node needs an Ed25519 keypair.**

This keypair signs org manifests, capability tokens, and snapshots
— it is the cryptographic root of the node's identity.

</div>

**Terminal A — Org A**

```bash
mkdir -p ~/stigmem-org-a && cd ~/stigmem-org-a

openssl genpkey -algorithm Ed25519 -out signing.key
openssl pkey -in signing.key -pubout -out signing.pub

export ORG_A_PUB=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | base64 | tr '+/' '-_' | tr -d '=')
export ORG_A_KEY_ID=$(openssl pkey -in signing.key -pubout -outform DER \
  | tail -c 32 | sha256sum | awk '{print $1}')
```

**Terminal B — Org B** (same commands in `~/stigmem-org-b`, exporting `ORG_B_PUB` and `ORG_B_KEY_ID`).

## Step 2 — Start both nodes

**Terminal A:**

```bash
cd ~/stigmem-org-a
STIGMEM_NODE_PRIVATE_KEY_FILE=signing.key \
STIGMEM_ENTITY_URI=stigmem://org-a.example \
STIGMEM_PORT=8100 \
STIGMEM_FEDERATION_ENABLED=true \
STIGMEM_TRUST_MODE=strict \
STIGMEM_ADMIN_KEY=secret-admin-a \
  stigmem serve &

curl -s http://localhost:8100/.well-known/stigmem | jq .
```

**Terminal B:** same with `STIGMEM_ENTITY_URI=stigmem://org-b.example`, `STIGMEM_PORT=8200`, `STIGMEM_ADMIN_KEY=secret-admin-b`.

## Step 3 — Publish org manifests

```bash
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
EXPIRES=$(date -u -d '+1 year' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
          || date -u -v+1y +%Y-%m-%dT%H:%M:%SZ)

# Terminal A — publish Org A manifest
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

<div className="stigmem-keypoint">

**`__self_sign__` is a reference-node shortcut.**

The reference node accepts the literal `__self_sign__` for the
`signature` field when `STIGMEM_NODE_PRIVATE_KEY_FILE` is configured.
For production deployments, compute the JCS-canonical signature
externally.

</div>

Repeat in Terminal B with `ORG_B_PUB` / `ORG_B_KEY_ID`.

### Register as federation peers

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
  -H "Authorization: Bearer secret-admin-b" \
  -H "Content-Type: application/json" \
  -d '{
    "peer_url": "http://localhost:8100",
    "peer_entity_uri": "stigmem://org-a.example"
  }' | jq .
```

## Step 4 — Create a quarantine garden on Org A

<div className="stigmem-keypoint">

**With `STIGMEM_TRUST_MODE=strict`, Org A will quarantine facts from Org B until trust is established.**

Create a quarantine garden first so quarantined facts have a home.

</div>

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

# Designate it as the node-level quarantine sink
curl -s -X PATCH http://localhost:8100/v1/admin/config \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{\"quarantine_garden_id\": \"$QUARANTINE_ID\"}" | jq .
```

## Step 5 — Issue a capability token from Org A to Org B

```bash
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

TOKEN_ID=$(echo "$TOKEN_RESPONSE" | jq -r '.token_id')
TOKEN_JSON=$(echo "$TOKEN_RESPONSE" | jq -r '.token_json')
```

**Verify the token (from Terminal B's perspective):**

```bash
curl -s -X POST http://localhost:8100/v1/federation/capability-tokens/verify \
  -H "Content-Type: application/json" \
  -d "{\"token_json\": $TOKEN_JSON}" | jq .
# → { "valid": true }
```

The six-step verification (§19.3.3) checks token version, expiry, issuer manifest, signature, subject delegation, and revocation status.

## Step 6 — Write a fact from Org B; observe quarantine

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

<div className="stigmem-keypoint">

**The fact is stored but isolated.**

It will not appear in normal `GET /v1/facts` queries until a
moderator admits it.

</div>

**Confirm the fact is in quarantine:**

```bash
# Terminal A — list pending quarantine items
curl -s "http://localhost:8100/v1/quarantine?quarantine_status=pending" \
  -H "Authorization: Bearer secret-admin-a" | jq .
```

## Step 7 — Admit the fact

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

`target_garden_id: null` promotes the fact to the main fact store (outside any garden boundary). Pass a garden UUID to promote into a specific garden instead.

**To reject the fact** (sets `confidence = 0`, retains for audit):

```bash
curl -s -X POST "http://localhost:8100/v1/gardens/$QUARANTINE_ID/reject" \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d "{\"fact_id\": \"$FACT_ID\", \"reason\": \"Source unverified.\"}" | jq .
```

## Step 8 — Verify the provenance chain

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

<div className="stigmem-keypoint">

**The `attestation_chain` contains Org B's Ed25519 signature over the fact body.**

The `source_trust` snapshot records the trust score at write time;
effective confidence at recall time uses the live recomputed score.

</div>

## Step 9 — Revoke the capability token

```bash
# Terminal A — revoke the token
curl -s -X POST "http://localhost:8100/v1/federation/capability-tokens/$TOKEN_ID/revoke" \
  -H "Authorization: Bearer secret-admin-a" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Tutorial complete; token no longer needed."}' | jq .
```

After revocation, a fresh verify call returns `{"valid": false, "reason": "revoked"}`.

## What you built

<div className="stigmem-fields">

<div>
<dt>Capability</dt>
<dt><span className="stigmem-fields__type">Mechanism</span></dt>
<dd>How it works</dd>
</div>

<div>
<dt>Distinct node identities</dt>
<dt><span className="stigmem-fields__type">Ed25519 keypair</span></dt>
<dd>Manifests anchor the key to an org URI.</dd>
</div>

<div>
<dt>Org manifests + transparency log</dt>
<dt><span className="stigmem-fields__type">PUT /v1/federation/manifest</span></dt>
<dd>Inclusion proof returned and stored.</dd>
</div>

<div>
<dt>Peer trust</dt>
<dt><span className="stigmem-fields__type">/v1/federation/peers</span></dt>
<dd>Federation pulls scoped facts using signed peer tokens.</dd>
</div>

<div>
<dt>Capability token</dt>
<dt><span className="stigmem-fields__type">24h write grant</span></dt>
<dd>Org A issued; Org B presented on every write.</dd>
</div>

<div>
<dt>Quarantine path</dt>
<dt><span className="stigmem-fields__type">source_trust &lt; threshold</span></dt>
<dd>Org B's first write landed in the quarantine garden.</dd>
</div>

<div>
<dt>Moderator admission</dt>
<dt><span className="stigmem-fields__type">/gardens/&#123;id&#125;/promote</span></dt>
<dd>Org A's admin promoted the quarantined fact.</dd>
</div>

<div>
<dt>Provenance chain</dt>
<dt><span className="stigmem-fields__type">Ed25519 attestation</span></dt>
<dd>Promoted fact carries Org B's signature; verifiable any time.</dd>
</div>

<div>
<dt>Token revocation</dt>
<dt><span className="stigmem-fields__type">/capability-tokens/&#123;id&#125;/revoke</span></dt>
<dd>Subsequent verify calls return <code>valid: false</code>.</dd>
</div>

</div>

## Next steps

<div className="stigmem-grid">

<div><h4>4-node topology</h4><p><a href="../concepts/federation/federation-4node.md">4-Node Federation guide</a> — N-node backpressure, relay configuration, scope propagation invariants (§6.7–6.8).</p></div>
<div><h4>Key rotation</h4><p>Rotate Org A's signing key without federation downtime — see the <a href="../concepts/federation/federation-trust.md">Federation Trust guide</a>.</p></div>
<div><h4>Trust mode tuning</h4><p>Lower <code>STIGMEM_QUARANTINE_TRUST_THRESHOLD</code> to admit more facts automatically from known peers.</p></div>
<div><h4>Encrypted storage</h4><p>Add <code>STIGMEM_AT_REST_ENCRYPTION=on</code> before going to production.</p></div>
<div><h4>Signed snapshots</h4><p>Back up both nodes — see the Backends guide.</p></div>

</div>
