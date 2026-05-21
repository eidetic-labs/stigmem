# Content-Addressed Fact IDs Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `stable` |
| First release | `0.9.0a1` spec lineage |
| Default surface | `default` |

CIDs are active core behavior. ADR-017 keeps them in the default node because
they are load-bearing for storage immutability, federation integrity, recall
hydration, and prompt-injection trust boundaries.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Monolithic spec lineage preserved content-addressed fact ID scope. | `spec/stigmem-spec-v0.9.0a1.md` |
| `v0.9.0a3` horizon | CID core/spec validation remains in active alpha scope. | `ROADMAP.md`; `docs/internal/releases/v0.9.0a3-roadmap.md` |

## Known Gaps

- Legacy rows may have `cid: null` until backfilled.
- Hash algorithm rotation beyond the `sha256:` prefix is not defined.
- Full federation policy for CID-null legacy facts remains owned by federation
  trust, not by this feature.

## Gates

- Default node computes CIDs for new facts.
- Read paths reject CID mismatches.
- CID verification and backfill status surfaces exist.
- Feature-local projection cleanup remains ongoing while legacy spec/public
  docs wrappers point to this record.
