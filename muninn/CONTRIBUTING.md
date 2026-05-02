# Contributing to Muninn

Thanks for your interest in contributing. Muninn is a community spec — the goal is to get smart people with production experience to stress-test the design before it ossifies.

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
3. **Submit a PR** against the active spec file (e.g., `spec/muninn-spec-v0.2.md`). Reference the issue.
4. **Merge criteria:** ≥2 approvals from contributors who have merged at least one prior PR. The spec maintainer may veto with a written rationale.

For small fixes (typos, clarity, example corrections), skip the RFC issue and send a PR directly.

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
