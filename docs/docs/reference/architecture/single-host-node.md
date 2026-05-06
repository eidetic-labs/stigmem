---
title: "Single-Host Node"
sidebar_label: "Single-Host Node"
sidebar_position: 1
description: "Architecture diagram of a single Stigmem node — FastAPI server, SQLite storage, HLC, auth, and background tasks."
audience: Spec
---

# Single-Host Node

*Audience: engineers deploying or contributing to the Stigmem reference node.*

A single Stigmem node is a self-contained FastAPI process backed by SQLite (or libSQL/Postgres). This diagram shows the internal component layout and request flow.

```mermaid
graph TB
    Client["Client\n(Agent, Adapter, SDK)"]

    subgraph Node["Stigmem Node (single host)"]
        direction TB
        API["FastAPI Router\n/v1/facts, /v1/gardens,\n/v1/recall, /v1/conflicts"]
        Auth["Auth Middleware\nAPI key → identity\n(§3.5)"]
        Attest["Source Attestation\nenforce | warn | off\n(§18)"]
        HLC["HLC Clock\nthreading.Lock-protected\n(§2.4)"]
        Ingest["Fact Ingest\nidempotent, CID-checked"]
        Conflict["Conflict Detector\nsame (entity, relation, scope)\n→ contradiction record\n(§3.3)"]
        Decay["Decay Sweeper\nbackground task\n(§15)"]
        FedPull["Federation Pull\nbackground task\nHLC-cursor replication\n(§6.3)"]

        subgraph Storage["Storage Layer"]
            DB[("facts\nconflicts\npeers\ngardens\napi_keys")]
            Vec[("vec_facts\nembedding index\n(§20)")]
            Edges[("entity_edges\ngraph index\n(§20)")]
        end
    end

    Client -- "HTTP/JSON\nBearer token" --> API
    API --> Auth
    Auth --> Attest
    Attest --> HLC
    HLC --> Ingest
    Ingest --> DB
    Ingest --> Conflict
    Conflict --> DB
    Ingest --> Vec
    Ingest --> Edges
    Decay --> DB
    Decay --> Vec
    FedPull --> Ingest
```

## Key components

| Component | File | Responsibility |
|-----------|------|---------------|
| FastAPI Router | `main.py`, `routes/` | HTTP endpoint registration, lifespan management |
| Auth Middleware | `auth.py` | Resolves `Authorization: Bearer` to an identity with scopes and permissions |
| Source Attestation | `auth.py` | Validates `source` URI against caller's `entity_uri` (§18) |
| HLC Clock | `hlc.py` | Thread-safe hybrid logical clock; advances on local writes and federated receives |
| Fact Ingest | `routes/facts.py` | Idempotent fact insertion, CID computation, scope enforcement |
| Conflict Detector | `routes/facts.py` | Detects `(entity, relation, scope)` value divergence; creates contradiction records |
| Decay Sweeper | `decay.py` | Background task that expires facts past `valid_until` or low confidence (§15) |
| Federation Pull | `federation_pull.py` | Periodically fetches new facts from registered peers using HLC cursor (§6.3) |
| Storage | `db.py` | SQLite/libSQL/Postgres with migration support; `vec_facts` and `entity_edges` for recall |
