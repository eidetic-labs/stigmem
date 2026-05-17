# ADR-015 Certification Results

This directory holds reviewed ADR-015 certification metadata and live-provider
result JSON.

`index.json` is the public certification index consumed by docs and validation
scripts. The index can represent certified, provisional, uncertified, expired,
and review-needed states without treating deterministic dry-run output as a live
model result.

Provider-backed result files are generated with:

```sh
uv run python scripts/run_adversarial_conformance.py \
  --provider <openai|anthropic|ollama> \
  --model <model-id>
```

Result files are not published as certified until reviewed. Dry-run providers
remain useful for schema and rubric smoke tests, but they must not be added to
the reviewed live-result list.
