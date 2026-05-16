# ADR-015 Corpus v1

This directory contains the seed prompt-injection corpus for ADR-015 consumer-layer conformance. It is separate from protocol-level adversarial vectors in `data/conformance/adversarial/protocol/` and from the legacy eval harness under `eval/corpus/adversarial/`.

Corpus patterns model untrusted fact content that an adapter or model must keep in the content channel. These files are not live model certification results; they are the versioned test inputs that later certification runners consume.

Run validation with:

```sh
uv run python scripts/validate_adversarial_corpus.py
```

Patterns are immutable once added. If a pattern becomes obsolete, add `deprecated_in` instead of editing its meaning.
