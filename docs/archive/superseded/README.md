# docs/archive/superseded — duplicate-loser pages

This directory holds pages that were duplicates or near-duplicates of canonical pages, archived after the content deduplication pass per master-checklist §4.3a.

## Convention

Each page here:

1. Was the **non-canonical** voice on a topic that had multiple pages.
2. Had its unique content **harvested into the canonical page** before moving.
3. Retains its **original repo path** under this directory (e.g., `superseded/concepts/recall/memory-gardens.md` was originally at `concepts/recall/memory-gardens.md`).
4. Has a header pointer to the canonical version.
5. Has a `client-redirects` rule from its original URL to the canonical URL in `docs/docusaurus.config.js`.

## Why archive instead of delete

Per master-checklist §4.3a binding preservation principle: **no feature, spec section, concept page, or design artifact is deleted in the docs restructure PR.** The duplicate is preserved so:

- The harvest is auditable — anyone questioning the merge can compare against the original.
- The original framing is recoverable — if it turns out one of the duplicates' phrasings was load-bearing for a different audience, it can be restored.
- External links don't 404 — `client-redirects` ensures the URL resolves.

## What's NOT here

Pages that were unambiguously wrong (e.g., a page with stale Status frontmatter that the canonical version corrected) get **fixed in the canonical version**, not archived. Archive is for genuine duplicates with content worth preserving.

Pages that were placeholders without real concepts go to `placeholder-pages/`, not here.

Pages that described features deferred to `experimental/<feature>/` go to that location, not here.

## Cross-references

- [`docs/archive/`](../) — parent index.
- [ADR-005](../../adr/005-docs-ia.md) — docs IA, "one canonical page per topic" principle.
