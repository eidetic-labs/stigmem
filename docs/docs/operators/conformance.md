---
title: Conformance Testing
sidebar_label: Conformance
audience: Integrator
---

# Conformance Testing

<p className="stigmem-meta"><span>5 min read</span><span>Protocol implementer · Contributor</span><span>Multi-backend</span></p>

<div className="stigmem-lead">

**What this page covers**

Two complementary conformance layers: machine-readable wire vectors
for the HTTP API, and a behavioral suite that exercises the full
fact/recall/graph/decay/federation/contradiction contract across
SQLite, libSQL, and Postgres.

</div>

**Audience:** protocol implementers validating a Stigmem node; contributors adding or changing spec behaviour; operators of forks or alternative backend implementations.

## Overview

<div className="stigmem-fields">

<div>
<dt>Layer</dt>
<dt><span className="stigmem-fields__type">Audience</span></dt>
<dd>What it tests</dd>
</div>

<div>
<dt><strong>Wire conformance</strong></dt>
<dt><span className="stigmem-fields__type">spec contributors</span></dt>
<dd>HTTP wire format and response shape against machine-readable JSON vectors.</dd>
</div>

<div>
<dt><strong>Multi-backend behavioral suite</strong></dt>
<dt><span className="stigmem-fields__type">backend implementers · CI</span></dt>
<dd>Full behavioral contract across SQLite, libSQL, and Postgres.</dd>
</div>

</div>

## Wire conformance

<div className="stigmem-keypoint">

**The current wire-vector suite is the executable test contract for the v0.9.0a1 wire format.**

The files still live under `data/conformance/v1.0/` for compatibility
with the pre-reset harness naming — treat that directory name as
historical, not as a claim that v1.0 has shipped.

</div>

### Running the suite

```bash
# From the repo root
uv run pytest node/tests/conformance/test_conformance_v1.py -v
```

The runner starts an in-process test node, executes every vector against it, and fails on any regression. **Zero skips are enforced** — if your change causes a vector to be skipped, CI will fail.

To run a single vector group:

```bash
uv run pytest node/tests/conformance/test_conformance_v1.py -v -k "garden"
```

### CI

The **Conformance** workflow ([`conformance.yml`](https://github.com/eidetic-labs/stigmem/blob/main/.github/workflows/conformance.yml)) runs automatically on every push to `main` and on pull requests that touch `node/`, `spec/`, `data/conformance/`, or the workflow file.

[![Conformance](https://github.com/eidetic-labs/stigmem/actions/workflows/conformance.yml/badge.svg)](https://github.com/eidetic-labs/stigmem/actions/workflows/conformance.yml)

### Vector groups

<div className="stigmem-fields">

<div>
<dt>File</dt>
<dt><span className="stigmem-fields__type">Spec coverage</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>01_fact_assert.json</code></dt>
<dt><span className="stigmem-fields__type">Spec-01, Spec-03</span></dt>
<dd>Fact assert wire format, all FactValue types.</dd>
</div>

<div>
<dt><code>02_fact_query.json</code></dt>
<dt><span className="stigmem-fields__type">Spec-03, Spec-15</span></dt>
<dd>Query, single-fact GET, retraction.</dd>
</div>

<div>
<dt><code>03_wellknown.json</code></dt>
<dt><span className="stigmem-fields__type">Spec-03</span></dt>
<dd><code>/.well-known/stigmem</code> discovery endpoint.</dd>
</div>

<div>
<dt><code>04_gardens.json</code></dt>
<dt><span className="stigmem-fields__type">Spec-02</span></dt>
<dd>Memory Garden CRUD, role management.</dd>
</div>

<div>
<dt><code>05_garden_facts.json</code></dt>
<dt><span className="stigmem-fields__type">Spec-02, Spec-01</span></dt>
<dd>Garden-tagged fact writes and ACL enforcement.</dd>
</div>

</div>

### Adding a new vector

:::note Requirement
Every new spec section or wire-format change MUST include at least one new conformance vector. PRs that add or modify spec text without a corresponding vector will not be merged.
:::

<ol className="stigmem-steps">
<li>Add to an existing group file that covers the relevant spec section. If no group exists, create a new numbered file (e.g. <code>06_my_feature.json</code>).</li>
<li>Follow the vector structure (see below).</li>
<li>Run <code>uv run pytest node/tests/conformance/test_conformance_v1.py -v</code> locally before opening a PR.</li>
</ol>

**Vector structure:**

```json
{
  "spec_section": "§X.Y",
  "title": "Short group title",
  "description": "Optional longer description",
  "vectors": [
    {
      "id": "unique-kebab-id",
      "description": "What this vector tests",
      "method": "POST",
      "path": "/v1/facts",
      "body": { ... },
      "expected_status": 201,
      "expected_body_contains": { "entity": "stigmem://testnode/user/alice" },
      "expected_body_has_keys": ["id", "timestamp"]
    }
  ]
}
```

**Assertion fields:**

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Checks</dd>
</div>

<div>
<dt><code>expected_status</code></dt>
<dt><span className="stigmem-fields__type">int</span></dt>
<dd>HTTP response status code.</dd>
</div>

<div>
<dt><code>expected_body_contains</code></dt>
<dt><span className="stigmem-fields__type">object</span></dt>
<dd>Top-level response keys equal these values.</dd>
</div>

<div>
<dt><code>expected_body_has_keys</code></dt>
<dt><span className="stigmem-fields__type">string[]</span></dt>
<dd>Response object includes these keys (any value).</dd>
</div>

<div>
<dt><code>expected_nested</code></dt>
<dt><span className="stigmem-fields__type">object</span></dt>
<dd>Dotted-path assertions into the response.</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Do not add vectors with `requires_auth: true`.**

Zero skips are enforced and auth-dependent scenarios belong under
`node/tests/auth/`.

</div>

## Multi-backend behavioral suite

The behavioral suite in `node/src/stigmem_conformance/tests/` exercises the full behavioral contract against **SQLite**, **libSQL**, and **Postgres**.

### In-process (simplest, no external services)

```bash
# SQLite (default — no dependencies)
python -m stigmem_conformance --backend sqlite

# libSQL (requires libsql-experimental)
pip install 'stigmem-node[libsql]'
python -m stigmem_conformance --backend libsql
```

### Postgres

```bash
# Start a local Postgres instance (Docker)
docker run -d -e POSTGRES_PASSWORD=test -p 5432:5432 postgres:16

# Install dependencies
pip install 'stigmem-node[postgres,conformance]'

# Run
STIGMEM_TEST_PG_DSN="postgresql://postgres:test@localhost/postgres" \
python -m stigmem_conformance --backend postgres
```

### Generate a Markdown report

```bash
python -m stigmem_conformance --backend sqlite --report conformance-sqlite.md
```

The report includes pass/fail counts, test details, and failure traces. Suitable for committing alongside a release or embedding in operator documentation.

### Via pytest directly

```bash
# All backends (skips unavailable ones automatically)
uv run pytest node/src/stigmem_conformance/tests/ -v

# Pin to one backend
uv run pytest node/src/stigmem_conformance/tests/ --conformance-backend=sqlite -v
```

### Test domains

<div className="stigmem-fields">

<div>
<dt>Module</dt>
<dt><span className="stigmem-fields__type">Tests</span></dt>
<dd>Skip conditions</dd>
</div>

<div>
<dt><code>test_facts.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Fact assert, query, retraction, TTL, validation. No skips.</dd>
</div>

<div>
<dt><code>test_recall.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Recall endpoint, token budget, scope isolation, response shape.</dd>
</div>

<div>
<dt><code>test_graph.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Graph neighbors, depth traversal, scope filter, retraction cleanup.</dd>
</div>

<div>
<dt><code>test_decay_synthesis.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Synthesize endpoint, decay sweeper, confidence ordering.</dd>
</div>

<div>
<dt><code>test_contradiction.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Contradiction detection, conflict list, resolution.</dd>
</div>

<div>
<dt><code>test_embeddings.py</code></dt>
<dt><span className="stigmem-fields__type">SQLite-only</span></dt>
<dd>Recall without vector index; vector tests. Skipped on libSQL/Postgres (sqlite-vec not applicable).</dd>
</div>

<div>
<dt><code>test_provenance.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Audit trail, source attribution, recall_id/query_hash.</dd>
</div>

<div>
<dt><code>test_federation.py</code></dt>
<dt><span className="stigmem-fields__type">core</span></dt>
<dd>Well-known endpoint, peer registration, pull API shape.</dd>
</div>

</div>

### Interpreting the report

<div className="stigmem-fields">

<div>
<dt>Status</dt>
<dt><span className="stigmem-fields__type">Symbol</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt>passed</dt>
<dt><span className="stigmem-fields__type">✅</span></dt>
<dd>Backend behaves correctly for this scenario.</dd>
</div>

<div>
<dt>failed</dt>
<dt><span className="stigmem-fields__type">❌</span></dt>
<dd>Behavioral regression — must be fixed before shipping.</dd>
</div>

<div>
<dt>skipped</dt>
<dt><span className="stigmem-fields__type">⏭</span></dt>
<dd>Feature not applicable to this backend (justified skip).</dd>
</div>

</div>

<div className="stigmem-keypoint">

**A report with zero failures and only justified skips means the backend is conformant.**

</div>

### Extending the suite

<ol className="stigmem-steps">
<li>Create <code>node/src/stigmem_conformance/tests/test_&lt;domain&gt;.py</code>.</li>
<li>Use only the HTTP API — no direct DB access.</li>
<li>Use the <code>conformance_client</code> fixture (parametrized over all backends).</li>
<li>Add <code>pytest.skip(reason="...")</code> for backend-specific features with a clear justification string.</li>
<li>Update the test-domains table above.</li>
</ol>

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

The `conformance-multi-backend` job runs all three backends in parallel. A `conformance-gate` job ensures all three are green before a PR can merge. The Postgres backend is feature-flagged (via the `postgres` extras and `STIGMEM_TEST_PG_DSN` env var) and runs against a GitHub-hosted Postgres 16 service.

## Spec citations

Every vector group file declares the modular spec it covers. Keep these citations up to date with the canonical spec composition in [`spec/PROTOCOL.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/PROTOCOL.md).

<div className="stigmem-keypoint">

**When the spec and a vector disagree, the spec is authoritative.**

Update the vector and open a bug report for the reference node.

</div>
