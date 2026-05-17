# ADR-015 Certification Results

This directory holds reviewed ADR-015 certification metadata and live-provider
result JSON.

`index.json` is the public certification index consumed by docs and validation
scripts. The index can represent certified, provisional, uncertified, expired,
and review-needed states without treating deterministic dry-run output as a live
model result.

Provider-backed result files are generated with:

```sh
export STIGMEM_ADR015_RESULTS_DIR="$HOME/Desktop/stigmem-local-artifacts/adr-015/runs"
uv run python scripts/run_adversarial_conformance.py \
  --provider <openai|anthropic|ollama> \
  --model <model-id>
```

Result files are not published as certified until reviewed. Dry-run providers
remain useful for schema and rubric smoke tests, but they must not be added to
the reviewed live-result list.

By default, the runner writes raw result JSON outside the repository at
`$STIGMEM_ADR015_RESULTS_DIR` or `~/.stigmem/adr-015-results`. Keep raw outputs
outside the worktree. Copy only explicitly reviewed and approved sanitized
artifacts into this directory.

## Publication Standard

Raw runner output is review input. It is not committed directly unless the
reviewer has confirmed that no sensitive model output is present. The normal
publication path is:

1. Run the live provider adapter with approved credentials or an approved local
   endpoint. Write raw output to the local-only artifact store, not the repo.
2. Review the raw JSON locally.
3. Generate a sanitized evidence file:

   ```sh
   uv run python scripts/sanitize_adversarial_result.py \
     data/conformance/adversarial/results/<raw-result>.json \
     data/conformance/adversarial/results/<reviewed-result>.json
   ```

4. Generate a draft per-pattern reviewer assessment:

   ```sh
   uv run python scripts/assess_adversarial_result.py \
     data/conformance/adversarial/results/<reviewed-result>.json \
     data/conformance/adversarial/results/<assessment>.json
   ```

5. Review the sanitized evidence file, per-pattern assessment, and written
   interpretation together.
6. Add the reviewed result row to `index.json` only after the evidence and
   interpretation are accepted.
7. Run `uv run python scripts/validate_adversarial_results.py`.

The corpus prompts themselves are public test vectors. Reviewed public evidence
should include aggregate scores, pattern IDs, categories, severities, the corpus
input, expected behavior, rubric outcomes, rubric notes, short sanitized
response excerpts, and reviewer assessments (`safe`, `unsafe`, `ambiguous`, or
`rubric-miss`). It should not include full raw model transcripts by default.

Raw result files should be kept outside the repository worktree whenever
possible. If a raw file is generated in this directory during local review,
delete it after producing the sanitized evidence and assessment artifacts.

Use stable redaction labels when sensitive content appears:

- `[REDACTED:api-key]`
- `[REDACTED:bearer-token]`
- `[REDACTED:local-path]`
- `[REDACTED:email]`
- `[REDACTED:environment-assignment]`
- `[REDACTED:system-prompt]` when a model appears to disclose hidden system,
  developer, adapter, or tool instructions.

If a model discloses content that looks like real hidden prompt/tool/system
text, keep the result local until the disclosure is reviewed and summarized in
non-sensitive terms.
