---
id: cost-calculator
title: Cost Calculator
sidebar_label: Cost Calculator
description: Estimate storage growth, network egress, embedding spend, and operator time before committing to Stigmem infrastructure.
---

# Cost Calculator

**Audience:** operators and engineering managers planning a Stigmem deployment.

This page explains the cost model inputs and outputs. A downloadable spreadsheet template lets you plug in your numbers and adjust assumptions.

**[Download the spreadsheet template](/stigmem-cost-calculator.csv)**

---

## Input variables

| Input | Description | Example |
|---|---|---|
| `facts_per_day` | Average facts asserted per day across all agents | 10 000 |
| `agents_per_day` | Average number of active agents per day | 50 |
| `backend` | Storage backend: `sqlite`, `libsql`, or `postgres` | `libsql` |
| `region_count` | Number of geographic regions (affects egress multiplier) | 2 |
| `embed_provider` | Embedding provider: `ollama`, `openai`, `voyage` | `openai` |
| `embed_model` | Model name (affects cost per token) | `text-embedding-3-small` |
| `federation_peers` | Number of federated peer nodes | 3 |
| `retention_days` | How long facts are retained before decay | 365 |

---

## Output estimates

### Storage growth

Each fact stores:

- **Core record:** entity URI + relation + value (avg ~150 bytes)
- **Embedding vector:** `STIGMEM_EMBED_DIMENSIONS` × 4 bytes (default 768 × 4 = 3 072 bytes)
- **Metadata:** HLC timestamp, confidence, source attestation (~100 bytes)

**Per-fact storage footprint:** approximately **3.5 KB** with default embeddings.

```
storage_growth_gb_per_year = facts_per_day × 365 × 3.5 KB / 1 GB
```

| facts/day | GB/year (est.) |
|---|---|
| 1 000 | 1.3 GB |
| 10 000 | 13 GB |
| 100 000 | 128 GB |
| 1 000 000 | 1.3 TB |

:::note
These are raw storage estimates. SQLite WAL headroom, Postgres WAL, and backup storage add ~2–3× overhead in practice.
:::

### Network egress

Egress occurs for:
- **Federation pull replication:** each peer pulls changed facts on every interval. Rough estimate: 1 KB per new fact × facts per pull cycle.
- **Multi-region libSQL sync:** embedded replica syncs to the Turso primary. Size ≈ facts written × per-fact payload.
- **API responses:** depends on query patterns; typically negligible compared to replication.

```
federation_egress_gb_per_month ≈ facts_per_day × federation_peers × 1 KB × 30 / 1 GB × region_count
```

Egress pricing varies by cloud provider (typically $0.08–$0.12/GB after free tiers). Use the spreadsheet to plug in your provider's rate.

### Embedding token cost

Only relevant for cloud embedding providers (OpenAI, Voyage). Ollama is offline with no per-token cost.

| Provider | Model | Dimensions | Cost per 1M tokens |
|---|---|---|---|
| OpenAI | `text-embedding-3-small` | 1 536 | ~$0.02 |
| OpenAI | `text-embedding-3-large` | 3 072 | ~$0.13 |
| Voyage | `voyage-3-lite` | 512 | ~$0.01 |
| Ollama | any | 256–1 024 | $0.00 (self-hosted) |

Average fact value: ~30 tokens.

```
embed_cost_per_month = facts_per_day × 30 × 30 / 1_000_000 × cost_per_1m_tokens
```

| facts/day | OpenAI 3-small $/month | Voyage-3-lite $/month |
|---|---|---|
| 1 000 | $0.02 | $0.009 |
| 10 000 | $0.18 | $0.09 |
| 100 000 | $1.80 | $0.90 |
| 1 000 000 | $18.00 | $9.00 |

Embedding cost is rarely the dominant line item for most deployments.

### Operator-time band

Operator overhead (excluding initial setup) scales with deployment complexity:

| Deployment type | Monthly operator hours (est.) |
|---|---|
| Single-host SQLite, no federation | 0.5–1 h |
| Single-host libSQL/Turso, 1–3 peers | 1–2 h |
| Kubernetes / Helm, multi-region, 5+ peers | 3–6 h |
| Multi-tenant, compliance logging, active federation mesh | 6–12 h |

Costs to factor in:
- Backup monitoring and quarterly restore tests
- Key rotation (annually, or after any key exposure)
- Dependency / security update sweeps
- Federation peer onboarding and trust-score tuning

---

## Worked example

**Setup:** 10 000 facts/day, 50 agents, libSQL backend, 2 regions, OpenAI embeddings, 3 federation peers, 365-day retention.

| Line item | Estimate |
|---|---|
| Storage growth/year | 13 GB raw; ~30 GB with WAL + backups |
| Turso Pro storage | $0 for first 9 GB/mo; ~$3/mo over |
| Federation egress/month | ~0.9 GB → ~$0.07 (at $0.08/GB) |
| OpenAI embedding/month | ~$0.18 |
| Operator time/month | 1–2 h |
| **Total infra cost/month** | **< $10** |

For most self-hosted deployments at this scale, the dominant cost is **operator time**, not infrastructure.

---

## Spreadsheet template

The downloadable CSV template contains:
- Input fields with example values
- Pre-built formulas for all estimates above
- Per-provider egress rate lookup table
- A 3-year growth projection chart

**[Download stigmem-cost-calculator.csv](/stigmem-cost-calculator.csv)**

Open in Excel, Google Sheets, or LibreOffice Calc. Fill in the yellow input cells; all estimates update automatically.

---

## Cost reduction levers

| Lever | Impact |
|---|---|
| Switch to Ollama embeddings | Eliminates embedding API cost entirely |
| Enable decay / TTL | Caps storage growth for ephemeral fact workloads |
| Reduce federation pull interval | Cuts egress for low-change nodes (`STIGMEM_FEDERATION_PULL_INTERVAL_S=300`) |
| Single-region deployment | Halves or eliminates inter-region egress |
| SQLite on a cheap VPS | Near-zero managed-service cost; trade-off is device-loss risk |
