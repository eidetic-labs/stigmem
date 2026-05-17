# ADR-015 Corpus v1

This directory contains the seed prompt-injection corpus for ADR-015 consumer-layer conformance. It is separate from protocol-level adversarial vectors in `data/conformance/adversarial/protocol/` and from the legacy eval harness under `eval/corpus/adversarial/`.

Corpus patterns model untrusted fact content that an adapter or model must keep in the content channel. These files are not live model certification results; they are the versioned test inputs that later certification runners consume.

Run validation with:

```sh
uv run python scripts/validate_adversarial_corpus.py
```

Run the offline certification-harness smoke test with:

```sh
uv run python scripts/run_adversarial_conformance.py
```

The default provider is deterministic and credential-free. It verifies the
ADR-015 result schema, rubric, and tier calculation before live provider-backed
certification runs are added. The same runner also supports live provider
execution with `--provider openai`, `--provider anthropic`, or
`--provider ollama` when the corresponding credentials or local endpoint are
configured.

Patterns are immutable once added. If a pattern becomes obsolete, add `deprecated_in` instead of editing its meaning.
