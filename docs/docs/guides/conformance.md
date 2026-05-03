---
id: conformance
title: Conformance Testing
sidebar_label: Conformance
---

# Conformance Testing

**Audience:** protocol implementers validating a Stigmem node; contributors adding or changing spec behaviour.

The Stigmem v1.0 conformance suite is the normative test contract for the wire format. Any node implementation that passes every vector in `data/conformance/v1.0/` is a conforming Stigmem node.

## Running the suite

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

## Vector groups

| File | Spec sections covered |
|------|-----------------------|
| `01_fact_assert.json` | §2.7, §5.1 — fact assert wire format, all FactValue types |
| `02_fact_query.json` | §5.2–§5.5 — query, single-fact GET, retraction |
| `03_wellknown.json` | §5.21 — `/.well-known/stigmem` discovery endpoint |
| `04_gardens.json` | §17 — Memory Garden CRUD, role management |
| `05_garden_facts.json` | §17.3, §2.7 — garden-tagged fact writes and ACL enforcement |

## Adding a new vector

:::note Requirement
Every new spec section or wire-format change MUST include at least one new conformance vector. PRs that add or modify spec text without a corresponding vector will not be merged.
:::

### 1. Choose a file

Add to an existing group file that covers the relevant spec section. If no group exists, create a new numbered file: `06_my_feature.json`. The runner loads all files matching `0*.json` in sorted order.

### 2. Vector structure

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

### 3. Assertion fields

| Field | Type | What it checks |
|-------|------|----------------|
| `expected_status` | int | HTTP response status code |
| `expected_body_contains` | object | Top-level response keys equal these values |
| `expected_body_has_keys` | string[] | Response object includes these keys (any value) |
| `expected_nested` | object | Dotted-path assertions into the response (see below) |

Use `expected_nested` for deep assertions without matching the full response:

```json
"expected_nested": { "value.type": "number", "value.v": 42.5 }
```

This checks `response["value"]["type"] == "number"` and `response["value"]["v"] == 42.5`.

### 4. Ordering dependencies

Use `requires_setup` (another vector's `id`) to declare that a prerequisite vector must run first within the same DB session:

```json
{
  "id": "garden-fact-write",
  "requires_setup": "garden-create",
  ...
}
```

### 5. Auth-dependent vectors

Do **not** add vectors with `requires_auth: true` to files in `data/conformance/v1.0/`. Zero skips are enforced; auth-dependent scenarios belong in the dedicated auth test module (`node/tests/test_auth.py`).

### 6. Verify and commit

```bash
# Verify locally before opening a PR
uv run pytest node/tests/test_conformance_v1.py -v
```

The CI gate runs the same command with `STIGMEM_AUTH_REQUIRED=false` and `STIGMEM_SOURCE_ATTESTATION_MODE=warn` — ensure your vectors are not auth-sensitive.

## Spec citations

Every vector group file declares the `spec_section` it covers. Keep these citations up to date with the canonical spec ([§2–§18 in `spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)). When the spec and a vector disagree, the spec is authoritative — update the vector and open a bug report for the reference node.
