---
title: Conformance Testing
sidebar_label: Conformance
audience: Integrator
---

# Conformance Testing

**Audience:** protocol implementers validating a Stigmem node; contributors adding or changing spec behaviour; operators of forks or alternative backend implementations.

---

## Overview

Stigmem ships two complementary conformance layers:

| Layer | What it tests | Who uses it |
|-------|---------------|-------------|
| **Wire conformance (current vectors)** | HTTP wire format and response shape against machine-readable JSON vectors | Spec contributors; anyone checking API compatibility |
| **Multi-backend behavioral suite** | Full behavioral contract (facts, recall, graph, decay, federation, contradictions, embeddings, provenance) across SQLite, libSQL, and Postgres | Backend implementers; fork operators; CI |

---

## Wire conformance

The current wire-vector suite is the executable test contract for the v0.9.0a1 wire format while the project is in the alpha reset. The files still live under `data/conformance/v1.0/` for compatibility with the pre-reset harness naming; treat that directory name as historical, not as a claim that v1.0 has shipped.

### Running the suite

```bash
# From the repo root
uv run pytest node/tests/test_conformance_v1.py -v
```

The runner starts an in-process test node, executes every vector against it, and fails on any regression. Zero skips are enforced — if your change causes a vector to be skipped, CI will fail.

To run a single vector group:

```bash
uv run pytest node/tests/test_conformance_v1.py -v -k "garden"
```

### CI

The **Conformance** workflow ([`conformance.yml`](https://github.com/Eidetic-Labs/stigmem/blob/main/.github/workflows/conformance.yml)) runs automatically on every push to `main` and on pull requests that touch `node/`, `spec/`, `data/conformance/`, or the workflow file.

[![Conformance](https://github.com/Eidetic-Labs/stigmem/actions/workflows/conformance.yml/badge.svg)](https://github.com/Eidetic-Labs/stigmem/actions/workflows/conformance.yml)

### Vector groups

| File | Spec sections covered |
|------|-----------------------|
| `01_fact_assert.json` | §2.7, §5.1 — fact assert wire format, all FactValue types |
| `02_fact_query.json` | §5.2–§5.5 — query, single-fact GET, retraction |
| `03_wellknown.json` | §5.21 — `/.well-known/stigmem` discovery endpoint |
| `04_gardens.json` | §17 — Memory Garden CRUD, role management |
| `05_garden_facts.json` | §17.3, §2.7 — garden-tagged fact writes and ACL enforcement |

### Adding a new vector

:::note Requirement
Every new spec section or wire-format change MUST include at least one new conformance vector. PRs that add or modify spec text without a corresponding vector will not be merged.
:::

1. Add to an existing group file that covers the relevant spec section. If no group exists, create a new numbered file: `06_my_feature.json`.
2. Follow the vector structure (see below).
3. Run `uv run pytest node/tests/test_conformance_v1.py -v` locally before opening a PR.

#### Vector structure

Every vector group file is a JSON object with this top-level shape:

```json
{
  "spec_section": "§X.Y",
  "title": "Short group title",
  "description": "Optional longer description",
  "vectors": [...]
}
```

Each vector in the `vectors` array:

```json
{
  "id": "unique-kebab-id",
  "description": "What this vector tests",
  "method": "POST",
  "path": "/v1/facts",
  "body": {
    "entity": "stigmem://testnode/user/alice",
    "relation": "memory:role",
    "value": { "type": "string", "v": "engineer" },
    "source": "stigmem://testnode/agent/test",
    "confidence": 1.0,
    "scope": "company"
  },
  "expected_status": 201,
  "expected_body_contains": {
    "entity": "stigmem://testnode/user/alice"
  },
  "expected_body_has_keys": ["id", "timestamp"]
}
```

#### Assertion fields

| Field | Type | What it checks |
|-------|------|----------------|
| `expected_status` | int | HTTP response status code |
| `expected_body_contains` | object | Top-level response keys equal these values |
| `expected_body_has_keys` | string[] | Response object includes these keys (any value) |
| `expected_nested` | object | Dotted-path assertions into the response |

Do **not** add vectors with `requires_auth: true` — zero skips are enforced and auth-dependent scenarios belong in `node/tests/test_auth.py`.

---

## Multi-backend behavioral suite (the pre-reset multi-backend work)

The behavioral suite in `node/src/stigmem_conformance/tests/` exercises the full behavioral contract against all three storage backends: **SQLite**, **libSQL**, and **Postgres**.

### How to run

#### In-process (simplest, no external services)

```bash
# SQLite (default — no dependencies)
python -m stigmem_conformance --backend sqlite

# libSQL (requires libsql-experimental)
pip install 'stigmem-node[libsql]'
python -m stigmem_conformance --backend libsql
```

#### Postgres

```bash
# Start a local Postgres instance (Docker)
docker run -d -e POSTGRES_PASSWORD=test -p 5432:5432 postgres:16

# Install dependencies
pip install 'stigmem-node[postgres,conformance]'

# Run
STIGMEM_TEST_PG_DSN="postgresql://postgres:test@localhost/postgres" \
python -m stigmem_conformance --backend postgres
```

#### Generate a Markdown report

```bash
python -m stigmem_conformance --backend sqlite --report conformance-sqlite.md
```

The report includes pass/fail counts, test details, and failure traces. It is suitable for committing alongside a release or embedding in operator documentation.

#### Via pytest directly

```bash
# All backends (skips unavailable ones automatically)
uv run pytest node/src/stigmem_conformance/tests/ -v

# Pin to one backend
uv run pytest node/src/stigmem_conformance/tests/ --conformance-backend=sqlite -v
```

### Test domains

| Module | Tests | Skip conditions |
|--------|-------|-----------------|
| `test_facts.py` | Fact assert, query, retraction, TTL, validation | None |
| `test_recall.py` | Recall endpoint, token budget, scope isolation, response shape | None |
| `test_graph.py` | Graph neighbors, depth traversal, scope filter, retraction cleanup | None |
| `test_decay_synthesis.py` | Synthesize endpoint, decay sweeper, confidence ordering | None |
| `test_contradiction.py` | Contradiction detection, conflict list, resolution | None |
| `test_embeddings.py` | Recall without vector index; vector tests | Skipped: libSQL/Postgres (sqlite-vec not applicable) |
| `test_provenance.py` | Audit trail, source attribution, recall_id/query_hash | None |
| `test_federation.py` | Well-known endpoint, peer registration, pull API shape | None |

### Interpreting the report

| Status | Meaning |
|--------|---------|
| ✅ passed | Backend behaves correctly for this scenario |
| ❌ failed | Behavioral regression — must be fixed before shipping |
| ⏭ skipped | Feature not applicable to this backend (justified skip) |

A report with **zero failures** and **only justified skips** means the backend is conformant.

### Extending the suite

To add a new behavioral domain:

1. Create `node/src/stigmem_conformance/tests/test_<domain>.py`.
2. Use only the HTTP API — no direct DB access.
3. Use the `conformance_client` fixture (parametrized over all backends).
4. Add `pytest.skip(reason="...")` for backend-specific features with a clear justification string.
5. Update the table above in this doc.

```python
# Example: new domain test
from .conftest import ConformanceClient

class TestMyFeature:
    def test_something(self, conformance_client: ConformanceClient) -> None:
        if conformance_client.backend == "postgres":
            pytest.skip("feature X not supported on Postgres (pg_vector needed)")
        r = conformance_client.client.post("/v1/my-endpoint", json={...})
        assert r.status_code == 200
```

### CI matrix

The `conformance-multi-backend` job in `conformance.yml` runs all three backends in parallel. A `conformance-gate` job ensures all three are green before a PR can merge.

All three backends are required to be green. The Postgres backend is feature-flagged (via the `postgres` extras and `STIGMEM_TEST_PG_DSN` env var) and runs against a GitHub-hosted Postgres 16 service.

---

## Spec citations

Every vector group file declares the `spec_section` it covers. Keep these citations up to date with the canonical spec ([§2–§21 in `spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)). When the spec and a vector disagree, the spec is authoritative — update the vector and open a bug report for the reference node.
