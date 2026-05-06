---
title: Operators
sidebar_label: Overview
description: Self-hosting handbook for Stigmem node operators — backend selection, deploy recipes, federation, backup, monitoring, and cost planning.
audience: Operator
sidebar_position: 4
---

# Operators

**Audience:** self-hosting operators, infrastructure engineers, SREs.

This handbook covers everything you need to run a Stigmem node in production, from picking a storage backend to debugging recall latency.

---

## In this section

| Page | What you'll find |
|---|---|
| [Choose your backend](./backends/choose-backend) | Decision tree: SQLite vs libSQL vs Postgres |
| [Deploy runbooks](./runbooks/deploy-runbooks) | Step-by-step runbooks for Fly, Compose, Helm, systemd, and PaaS |
| [Federation peer setup](./runbooks/federation-setup) | Key generation, pinning, and source-trust tuning |
| [Backup & restore](./runbooks/backup-restore) | Signed snapshot workflow and cloud PITR |
| [Monitoring & debugging](./observability/monitoring) | Health checks, metrics, and recall-latency diagnosis |
| [Eval harness](./observability/eval-harness) | Automated evaluation and regression testing |
| [Cost calculator](./cost-calculator) | Estimating storage, egress, embedding, and operator costs |

---

## Quick orientation

A production Stigmem node has four operational concerns:

```
┌─────────────────────────────────────────────────────┐
│              Stigmem reference node                 │
│                                                     │
│  ┌────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Storage   │  │  Federation  │  │  Recall /  │  │
│  │  backend   │  │  peer mesh   │  │  embedding │  │
│  └────────────┘  └──────────────┘  └────────────┘  │
│            ↕               ↕               ↕        │
│  ┌──────────────────────────────────────────────┐   │
│  │            Operational layer                 │   │
│  │  backup/restore · key rotation · monitoring  │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Start here** if you haven't deployed yet:
1. [Choose your backend](./backends/choose-backend) — picks your persistence strategy.
2. [Deploy runbooks](./runbooks/deploy-runbooks) — gets the node running in your environment.
3. [Federation peer setup](./runbooks/federation-setup) — connects your node to peers.

**Day-two operations:**
- [Backup & restore](./runbooks/backup-restore) — protect against data loss.
- [Monitoring & debugging](./observability/monitoring) — observe and diagnose your node.

**Planning a deployment?** The [cost calculator](./cost-calculator) helps you estimate storage growth, egress, embedding spend, and operator time before you commit to infrastructure.
