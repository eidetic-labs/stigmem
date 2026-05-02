# Contributing to Muninn

Thanks for your interest in contributing. Muninn is a community spec — the goal is to get smart people with production experience to stress-test the design before it ossifies.

## Ways to contribute

| Track | What it is | Who it's for |
|---|---|---|
| **Design partner** | 30-min interview + async spec review + named co-author credit | Teams that have built agent memory, knowledge graphs, or agent coordination at scale |
| **RFC** | Propose a spec change via issue + PR | Anyone with a concrete problem or proposed improvement |
| **Implementation** | Build an alternative node or client | Developers who want to validate the wire format against real workloads |
| **Bug / gap report** | File an issue about a spec ambiguity or prototype bug | Anyone reading the spec |

## Design partner track

Design partners have outsized influence on the spec. If you have production experience with agent memory (e.g., Zep, Letta/MemGPT, Cognee, LangMem, custom solutions), we want your feedback on the federation section in particular.

**To become a design partner:**
1. Open an issue with the label `design-partner` describing your use case and what you've built
2. We'll schedule a 30-minute call
3. You'll receive a draft PR of the federation section for async review
4. Merged contributions earn co-author credit in the spec

## RFC process

Use this when you want to propose a spec change, add a new field or endpoint, change semantics, or resolve an open question from §8.

1. **Open an RFC issue** using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml). Include:
   - The problem you're solving
   - Your proposed change
   - Alternatives you considered
   - Open questions
2. **Discuss** on the issue. Aim for at least one week of async discussion before calling for merge.
3. **Submit a PR** against the active spec file (e.g., `spec/loom-spec-v0.2.md`). Reference the issue.
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

The spec file records authors in its header. Design partners and RFC contributors who make substantive changes to spec content are listed. Implementation-only contributors are acknowledged in CHANGELOG.

## Code of conduct

Be direct and technically rigorous. Assume good faith. Disagree with arguments, not people. There is no formal CoC document yet; interim standard is the [Contributor Covenant v2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).

## License

By contributing, you agree your contributions are licensed under Apache-2.0 (same as the project).
