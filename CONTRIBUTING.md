# Contributing to Stigmem

Thanks for your interest in contributing. Stigmem is a community spec — the goal is to get smart people with production experience to stress-test the design before it ossifies.

## Ways to contribute

| Track | What it is | Who it's for |
|---|---|---|
| **RFC** | Propose a spec change via issue + PR | Anyone with a concrete problem or proposed improvement |
| **Implementation** | Build an alternative node or client | Developers who want to validate the wire format against real workloads |
| **Bug / gap report** | File an issue about a spec ambiguity or prototype bug | Anyone reading the spec |

## RFC process

Use this when you want to propose a spec change, add a new field or endpoint, change semantics, or resolve an open question from §8.

1. **Open an RFC issue** using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml). Include:
   - The problem you're solving
   - Your proposed change
   - Alternatives you considered
   - Open questions
2. **Discuss** on the issue. Aim for at least one week of async discussion before calling for merge.
3. **Submit a PR** against the active spec file (e.g., `spec/stigmem-spec-v0.2.md`). Reference the issue.
4. **Merge criteria:** ≥2 approvals from contributors who have merged at least one prior PR. The spec maintainer may veto with a written rationale.

For small fixes (typos, clarity, example corrections), skip the RFC issue and send a PR directly.

## Conformance suite

**Contract:** every new spec section or wire-format change MUST include at least one new conformance vector in `data/conformance/v1.0/`. PRs that add or modify spec text without a corresponding vector will not be merged.

The `data/conformance/v1.0/` directory contains machine-readable test vectors that every conforming implementation must pass. The CI job **Stigmem v1.0 Conformance Suite** runs on every push to `main` and on pull requests that touch `node/`, `spec/`, `data/conformance/`, or the workflow file itself.

**Run locally:**

```bash
uv run pytest node/tests/test_conformance_v1.py -v
```

**Adding a new test vector:**

1. Open (or create) a numbered file in `data/conformance/v1.0/` (e.g., `06_new_feature.json`). The runner loads all files matching `0*.json` in sorted order.
2. Use this top-level structure:

```json
{
  "spec_section": "§X.Y",
  "title": "Short group title",
  "description": "Optional longer description",
  "vectors": [...]
}
```

3. Each vector must include at minimum `id`, `description`, `method`, `path`, and one of the `expected_*` assertion fields:

```json
{
  "id": "unique-kebab-id",
  "description": "What this vector tests",
  "method": "POST",
  "path": "/v1/facts",
  "body": { "entity": "stigmem://node/user/alice", "relation": "memory:role", "..." },
  "expected_status": 201,
  "expected_body_contains": { "entity": "stigmem://node/user/alice" },
  "expected_body_has_keys": ["id", "timestamp"]
}
```

4. Use `expected_nested` for deep assertions without matching the full response. Keys are dotted paths:

```json
"expected_nested": { "value.type": "number", "value.v": 42.5 }
```

   This checks `response["value"]["type"] == "number"` and `response["value"]["v"] == 42.5`.

5. Use `requires_setup` (another vector's `id`) to declare ordering dependencies — the runner will execute the prerequisite first within the same DB session.

6. **Do not add vectors with `requires_auth: true` to files in `data/conformance/v1.0/`.** Zero skips are enforced by CI; auth-dependent scenarios belong in the dedicated auth test module.

## Prototype contributions

The prototype in `prototype/` is a minimal reference implementation — not production software. Contributions that validate spec behavior are welcome; contributions that add production-hardening, auth, or persistence layers should wait until Phase 2 scope is set.

To run it:

```bash
cd prototype
pip install -r requirements.txt
python main.py        # starts the local node on :8000
python seed_memory.py # loads example facts
```

Tests: `pytest` (when test coverage exists — contributions welcome).

## Spec authorship and attribution

The spec file records authors in its header. RFC contributors who make substantive changes to spec content are listed. Implementation-only contributors are acknowledged in CHANGELOG.

## Code of conduct

Be direct and technically rigorous. Assume good faith. Disagree with arguments, not people. There is no formal CoC document yet; interim standard is the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree your contributions are licensed under Apache-2.0 (same as the project).
