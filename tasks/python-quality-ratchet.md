# Python Quality Ratchet

## Goal

Move from staged Python baseline gating to zero-baseline strictness without destabilizing PR throughput.

## Current Guardrails

- Baseline gates still block regressions across the existing Python surface.
- PR CI now runs strict Ruff on changed Python files.
- PR CI now runs strict mypy on changed production Python files.

## Ratchet Strategy

1. Keep changed-file strictness enabled as the floor.
2. Burn down baseline debt package by package instead of repo-wide.
3. Remove a package from the baseline workflow only after it is zero-clean under strict tooling.
4. Never refresh the committed baselines upward except for an intentional, reviewed policy decision.
5. Prefer source-package cleanup before test-package cleanup when choosing sequence.

## Recommended Cleanup Order

1. `sdks/stigmem-py/src`
2. `node/src`
3. adapter source packages under `adapters/**`
4. test-only Python files once production surfaces are stable

## Exit Criteria

- Baseline files shrink monotonically.
- Changed-file strictness stays green during the cleanup.
- Individual packages graduate to zero-baseline strictness and stop depending on the debt baselines.
