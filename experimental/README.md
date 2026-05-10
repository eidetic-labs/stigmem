# Experimental Features

> Index of features deferred from v1.0 critical-path scope per [ADR-002](../docs/adr/002-v1-critical-path-scope.md).
> Each feature returns to default-on supported state only after passing all five gates in [ADR-008](../docs/adr/008-experimental-reintroduction-gates.md).
>
> **Status as of:** 2026-05-06 · **Active version:** v0.9.0a1

---

## How to use this document

- **Each feature has a `STATUS.md`** at `experimental/<feature>/STATUS.md` that tracks its gate progress.
- **The table below is the index.** Skim to see which features are progressing, which are dormant, and which have stalled.
- **No feature gets "almost there" status.** A feature has either passed a gate or it hasn't. Partial work toward a gate is tracked in the feature's STATUS.md notes, not in this index.
- **To propose work on an experimental feature:** read the feature's STATUS.md, identify the next ungated step, and open a discussion before submitting code. Per ADR-008, gate progress requires deliberate effort, not opportunistic PRs.

---

## Gate legend

The five gates from ADR-008:

| Gate | What it requires |
|---|---|
| 1 | Threat-model delta merged into `spec/security/deltas/` |
| 2 | ADR drafted and merged |
| 3 | Conformance vectors (positive, negative, **adversarial**) wired into CI |
| 4 | 30-day external operator soak with public bug reporting |
| 5 | Documentation parity across Learn / Build / Operate / Secure |

A feature must pass all five **in order** before it can return to default-on supported state.

Status notation: `1✓ 2✓ 3· 4· 5·` means gates 1 and 2 passed, gates 3–5 not yet.

---

## Index

### Protocol features

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| §17 Memory garden (ACL primitives) | [STATUS](17-memory-garden/STATUS.md) | `1· 2· 3· 4· 5·` | Dormant. Defer until base scope model is operator-validated. |
| §18 Source attestation | [STATUS](18-source-attestation/STATUS.md) | `1· 2· 3· 4· 5·` | Dormant. Extension of provenance; defer until base provenance is stable. |
| §21 Lazy instruction discovery | [STATUS](21-lazy-instruction-discovery/STATUS.md) | `1· 2· 3· 4· 5·` | **Blocked.** Needs ADR-003 capability foundation; redesign before reintroduction (R-15). |
| §23 RTBF tombstones | [STATUS](23-rtbf-tombstones/STATUS.md) | `1· 2· 3· 4· 5·` | Operationally complex (R-16, R-17); needs full operator runbook. |
| §24 Time-travel `as_of` queries | [STATUS](24-time-travel/STATUS.md) | `1· 2· 3· 4· 5·` | Coupled to §23; same operator-soak prerequisite. |
| §25 Content-Addressed Fact IDs (CIDs) | [STATUS](25-cids/STATUS.md) | `1· 2· 3· 4· 5·` | Field-exclusion semantics (R-18) need integration tests. |
| Subscriptions (push-based federation) | [STATUS](subscriptions/STATUS.md) | `1· 2· 3· 4· 5·` | Defer until pull-based replication is operator-validated. |

### Authentication & integration

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| OIDC integration | [STATUS](oidc/STATUS.md) | `1· 2· 3· 4· 5·` | New auth trust boundary; not threat-modeled adversarially. |
| Multi-tenant isolation | [STATUS](multi-tenant/STATUS.md) | `1· 2· 3· 4· 5·` | Adds tenant boundary on top of scopes. |
| Fuzzy entity-URI resolver | [STATUS](fuzzy-resolver/STATUS.md) | `1· 2· 3· 4· 5·` | Convenience feature; not on critical path. |

### Storage backends

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| PostgreSQL backend | [STATUS](postgres-backend/STATUS.md) | `1· 2· 3· 4· 5·` | Highest-priority storage candidate after SQLite operator-validates. |
| libSQL / Turso backend | [STATUS](libsql-backend/STATUS.md) | `1· 2· 3· 4· 5·` | Adds third-party trust dependency; reintroduce only on operator demand. |

### Embedding

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| Cloud embedding (OpenAI, etc.) | [STATUS](cloud-embedding/STATUS.md) | `1· 2· 3· 4· 5·` | R-20 (poisoning) accepted-with-warnings; needs divergence-check tooling. |

### Adapters & integrations

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| Obsidian adapter | [STATUS](obsidian-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Separate threat model (TB-6); worth doing after OpenClaw v0.9 validates the contract. |
| Letta adapter | [STATUS](letta-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| Zep adapter | [STATUS](zep-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| Cognee adapter | [STATUS](cognee-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| Gemini adapter | [STATUS](gemini-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| OpenAI-tools adapter | [STATUS](openai-tools-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| Paperclip adapter | [STATUS](paperclip-adapter/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after OpenClaw validation. |
| Curator dashboard | [STATUS](dashboard/STATUS.md) | `1· 2· 3· 4· 5·` | Defer until v1.0 stable; not on critical path. |

### SDKs

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| Go SDK | [STATUS](sdk-go/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after Python SDK is operator-validated. |
| TypeScript SDK | [STATUS](sdk-ts/STATUS.md) | `1· 2· 3· 4· 5·` | Same. |

### Deployment

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| Helm chart | [STATUS](deploy-helm/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce after Docker Compose is operator-validated. |
| Fly.io configuration | [STATUS](deploy-fly/STATUS.md) | `1· 2· 3· 4· 5·` | Same. |
| systemd unit files | [STATUS](deploy-systemd/STATUS.md) | `1· 2· 3· 4· 5·` | Same. |
| Grafana dashboards | [STATUS](deploy-grafana/STATUS.md) | `1· 2· 3· 4· 5·` | Reintroduce alongside Helm. |

### Operational

| Feature | STATUS | Gates | Notes |
|---|---|---|---|
| Billing hooks | [STATUS](billing/STATUS.md) | `1· 2· 3· 4· 5·` | Commercial concern; belongs in hosted offering, not OSS reference node. |

---

## Conventions

- **One STATUS.md per directory.** A feature's directory under `experimental/` contains the code (in subdirectories) and a `STATUS.md` at the directory root.
- **STATUS.md is updated, not rewritten.** Gate-progress entries are appended with dates; superseded entries are crossed out, not deleted. The history is the institutional memory.
- **Build status is independent of gate status.** A feature can be buildable (compiles, tests pass at the level the original author wrote them) without progressing gates. A feature that is unbuildable is marked accordingly in its STATUS.md.
- **No feature is "almost ready."** A feature is at gate N or it isn't.

---

## Adding a new experimental feature

When work begins on a feature that doesn't fit the v1.0 critical-path scope:

1. Create `experimental/<feature>/` and place the code there.
2. Create `experimental/<feature>/STATUS.md` from the [template](../STATUS-TEMPLATE.md).
3. Add an entry to this index.
4. Open a tracking issue tagged `experimental:<feature>`.

The feature lives in `experimental/` until it passes all five ADR-008 gates. It may be excluded from default builds, default test runs, and default documentation.

---

## Removing an experimental feature

Sometimes the answer is "this feature is not coming back." When that happens:

1. Update the feature's STATUS.md to status `Withdrawn` with a dated rationale.
2. Move the directory to `experimental/withdrawn/<feature>/` to preserve history.
3. Update this index to a "Withdrawn" section at the bottom.
4. Open a closing PR; do not delete the code outright. Withdrawals are reversible if circumstances change.

---

*This document is updated whenever a feature changes gate status. Per ADR-008, gate transitions require sign-off (two contributors or the founder alone, per ADR-001 §Contributor approval rule).*
