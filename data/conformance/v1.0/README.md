# Stigmem v1.0 Conformance Vectors

This directory contains machine-readable conformance test vectors that define
the v1.0 wire contract for the stigmem reference node.

Each JSON file is a vector group covering one area of the spec. The
`node/tests/test_conformance_v1.py` suite runs all vectors against a live
test node and fails on any regression.

## Adding a new vector

1. Add an entry to the appropriate `*.json` file (or create a new file).
2. Each vector has `id`, `description`, `request`, and `expected` fields.
3. Run `pytest node/tests/test_conformance_v1.py -v` to verify.
4. Per CONTRIBUTING.md: every new spec feature MUST add at least one vector.

## Files

- `facts.json` — §2 fact shape + §5.1–§5.6 fact CRUD wire format
- `auth.json` — §3.5 authentication + §5 auth routes
- `federation.json` — §6 federation wire format
- `gardens.json` — §17 Memory Garden CRUD
- `wellknown.json` — §5.21 /.well-known/stigmem discovery
