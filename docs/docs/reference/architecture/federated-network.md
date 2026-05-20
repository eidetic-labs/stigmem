---
title: "Federated Network"
sidebar_label: "Federated Network"
sidebar_position: 2
description: "Architecture diagram of a multi-node Stigmem federation — PeerDeclaration handshake, scope-filtered replication, and conflict resolution."
audience: Spec
---

# Federated Network

<p className="stigmem-meta"><span>2 min read</span><span>Federation engineer</span><span>Spec-05</span></p>

<div className="stigmem-lead">

**What this page covers**

Stigmem federation is pull-based: each node periodically fetches new
facts from registered peers using an HLC cursor. Peering is
established via mutual PeerDeclaration exchange, and replication
respects scope boundaries.

</div>

**Audience:** engineers implementing federation, deploying multi-node clusters, or reviewing `Spec-05-Federation-Trust`.

## Network topology

```mermaid
graph LR
    subgraph OrgA["Org A"]
        A["Node A\nscopes: local, team,\ncompany, public"]
    end

    subgraph OrgB["Org B"]
        B["Node B\nscopes: local, team,\ncompany, public"]
    end

    subgraph OrgC["Org C"]
        C["Node C\nscopes: local, team,\ncompany, public"]
    end

    A -- "public scope\nbidirectional" --- B
    B -- "public scope\nbidirectional" --- C
    A -. "no direct peering" .- C
```

<div className="stigmem-keypoint">

**Peering is pair-wise and explicit.**

Node A federates with Node B, and Node B federates with Node C, but
A and C have no direct peering. Facts flow A→B→C only if B's pull
from A and C's pull from B both cover the relevant scope.

</div>

## Handshake sequence

```mermaid
sequenceDiagram
    participant A as Node A
    participant B as Node B

    Note over A,B: Spec-05 — Mutual PeerDeclaration exchange

    A->>A: Generate PeerDeclaration<br/>target=B, scopes=[public],<br/>direction=bidirectional
    A->>A: Sign with Ed25519 federation key
    A->>B: POST /v1/federation/peers<br/>{declaration, signature}
    B->>B: Verify signature via<br/>A's /.well-known/stigmem
    B->>B: Generate reciprocal<br/>PeerDeclaration for A
    B->>A: POST /v1/federation/peers<br/>{declaration, signature}
    A->>A: Verify B's signature

    Note over A,B: Peering active — pull loops begin

    loop Every pull interval
        B->>A: GET /v1/federation/facts<br/>?since_hlc=<cursor>&scope=public
        A-->>B: Facts since cursor (≤500)
        B->>B: Idempotent ingest<br/>advance HLC cursor
    end
```

## Scope enforcement on federation

```mermaid
flowchart TB
    Fact["Outbound fact"]
    Check{"Scope allowed?"}
    Send["Replicate to peer"]
    Drop["Silently drop"]

    Fact --> Check
    Check -- "Yes" --> Send
    Check -- "No" --> Drop
```

Nodes enforce scope on both sides:

<div className="stigmem-grid">

<div><h4>Outbound</h4><p>Facts whose scope exceeds the PeerDeclaration's <code>allowed_scopes</code> are silently dropped.</p></div>
<div><h4>Inbound</h4><p>Facts whose scope exceeds what the peer is authorized to write are rejected and logged to the federation audit table.</p></div>

</div>

## Conflict on reunion

<div className="stigmem-keypoint">

**When two nodes write divergent values during a partition, both facts survive.**

On reunion the receiving node detects the contradiction and creates
a conflict record (`Spec-15-Fact-Semantics`). Resolution is explicit
via `POST /v1/conflicts/:id/resolve`.

</div>
