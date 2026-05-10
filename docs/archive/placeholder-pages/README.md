# docs/archive/placeholder-pages — preserved placeholders

This directory holds pages that were placeholders in earlier docs revisions — pages with a slot reserved for a concept or section that was either deferred indefinitely or never fully scoped.

## Convention

Each page here:

1. Was originally a placeholder (e.g., `spec/section-13.md` reserved for "Phase 5+" content).
2. Was reviewed for original intent during the master-checklist §4.3a "Stale-page evaluation" pass.
3. Had no real concept behind it (if a real concept existed, the page moved to `experimental/<feature>/` with `STATUS.md` instead).
4. Retains its **original repo path** under this directory (e.g., `placeholder-pages/spec/section-13.md`).
5. Has an explanatory header noting what the placeholder was reserved for.

## Why preserve placeholders

The placeholder slot itself is institutional memory: it says "we thought about this and reserved a number/section for it." Deleting placeholders erases that history. Adopters or future contributors who encounter a `§13` reference in older content can find the explanation here.

## Cross-references

- [`docs/archive/`](../) — parent index.
- [`experimental/`](../../../experimental/) — for placeholders that turned out to have real concepts behind them.
