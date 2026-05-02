---
id: federation
title: Federation
sidebar_label: Federation
---

# Federation

**Audience:** Node operators connecting multiple Stigmem nodes.

:::info Coming soon
Full federation guide content is planned for the next docs sprint.
:::

## Overview

Federation lets two Stigmem nodes exchange facts within agreed scopes. The full protocol is defined in spec §6.

High-level flow:

1. Node A registers with Node B (`POST /v1/federation/peers`) with an Ed25519 declaration signature
2. Node B verifies the signature against Node A's `/.well-known/stigmem` public key
3. Node A's background pull loop periodically fetches new facts from Node B using a scoped peer token

## Quick start

```bash
# 1. Get Node B's well-known metadata (for its node_id and pubkey)
curl http://nodeB:8000/.well-known/stigmem | jq .

# 2. Register Node A with Node B
#    (declaration_sig generation requires the Ed25519 key — see spec §6.1)
curl -X POST http://nodeB:8000/v1/federation/peers \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <nodeB-key>' \
  -d '{
    "node_id": "stigmem:node:nodeA",
    "node_url": "http://nodeA:8000",
    "allowed_scopes": ["company", "public"],
    "declaration_sig": "<base64url-sig>"
  }'

# 3. List peers on Node B
curl http://nodeB:8000/v1/federation/peers \
  -H 'X-API-Key: <nodeB-key>' | jq .
```

## Topics to be covered

- Generating Ed25519 keys and declaration signatures (spec §6.1)
- Peer token format and verification (spec §6.3)
- Scope enforcement and security invariants (spec §6.4)
- Monitoring the federation audit log
- Configuring `STIGMEM_FEDERATION_PULL_INTERVAL_S`

See the [Federation API Reference](/docs/api-reference) and the [Architecture overview](/docs/architecture) for internals.
