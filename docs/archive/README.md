# docs/archive — preservation of historical documentation

This directory preserves documentation artifacts that have been superseded, restructured, or are no longer canonical surface for the current release. **Per master-checklist §4.3a (binding preservation principle): no markdown file in this directory was deleted from the public repo.** Each artifact moved here from a previous canonical location with a `client-redirects` rule from its old URL to its current canonical equivalent (or to a "this URL was not a real release" landing where applicable).

## Subdirectories

### `snapshots/` — versioned-docs snapshots

Houses the `versioned_docs/` snapshots that were configured as Docusaurus versioned releases but never represented actual public ship-state. Specifically:

- `version-v1.1/` — snapshot configured under `lastVersion: v1.1`. The v1.1 release was never publicly tagged or shipped.
- `version-v0.2/` — historical evolutionary checkpoint.

Each snapshot retains its original Docusaurus structure for reference. URLs that pointed at `/v1.1/*` and `/v0.2/*` redirect to a "this URL was not a real release; see /docs/" landing page.

### `superseded/` — duplicate-loser pages from the content deduplication pass

Houses pages that were duplicates or near-duplicates of canonical pages. Per the deduplication-with-harvest convention (master-checklist §4.3a "Content deduplication pass"):

1. Canonical page chosen.
2. Unique content from the duplicate harvested into the canonical page.
3. Duplicate moved here under its original repo path (e.g., `superseded/concepts/recall/memory-gardens.md`) with a header pointer to the canonical version.
4. `client-redirects` rule from the original URL to the canonical URL.

The duplicates are preserved so the harvest is auditable and the original framing is recoverable if a question arises.

### `placeholder-pages/` — pages that lived without real content

Houses pages where the original page was a placeholder (e.g., `spec/section-13.md` reserved for "Phase 5+" without a real concept yet). These pages may have hosted a real concept that was later deferred — in those cases, the concept moved to `experimental/<feature>/` with a `STATUS.md`. When no real concept lived behind the placeholder, the page lands here with an explanatory header noting what the placeholder was meant for, preserving institutional memory.

## How to use this directory

- **Looking for a page that's no longer in the canonical tree?** Check `superseded/` for the original path.
- **Following an old `/v1.1/*` or `/v0.2/*` link?** The URL redirects; the source content lives under `snapshots/`.
- **Bringing content back?** When a `superseded/` page's content is needed, the canonical page is the source of truth — the `superseded/` copy is the historical record, not a re-merge target.

## Cross-references

- [`spec/archive/evolution/`](../../spec/archive/evolution/) — superseded evolutionary spec snapshots, similar pattern but for protocol-spec content.
- [`experimental/<feature>/`](../../experimental/) — features deferred from v1.0 critical-path scope per ADR-002, kept in the codebase pending re-introduction per [ADR-008](../adr/008-experimental-gates.md).
- [ADR-009](../adr/009-repo-structure.md) — repository structure and the `archive/` vs `experimental/` distinction.
