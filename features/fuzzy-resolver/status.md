# Fuzzy Resolver Status

## Lifecycle

| Field | Value |
| --- | --- |
| Status | `active` |
| Stability | `experimental` |
| First release | `0.9.0a1` |
| Default surface | `opt-in` |

Fuzzy resolver exists in the reference node as authenticated entity-resolution
and alias-management behavior. It remains experimental because broader matching
strategies and production tuning controls are not part of the stable default
surface.

## Release History

| Release | Change | Evidence |
| --- | --- | --- |
| `v0.9.0a1` | Fuzzy resolver behavior existed in the alpha-era node and was tracked as a deferred experimental feature. | `experimental/fuzzy-resolver/STATUS.md`; `node/tests/recall/test_fuzzy_resolver.py` |
| `0.9.xA` planned | Keep the feature outside the default critical path while deciding whether resolver behavior remains core or becomes a plugin-backed feature. | `ROADMAP.md`; `docs/internal/feature-tracker.md` |

## Gate Progress

| Gate | Description | Status | Evidence |
| --- | --- | --- | --- |
| Contract tests | Validate alias registration, alias deletion rules, query-path alias compatibility, and entity-resolution responses. | Partial | `node/tests/recall/test_fuzzy_resolver.py`; `node/tests/auth/test_peer_auth_resolver_b2.py` |
| Operator controls | Define tuning guidance for threshold, candidate limits, and false-positive handling. | Open | None currently recorded. |
| Security review | Confirm entity-existence and alias-management disclosure boundaries. | Open | `features/fuzzy-resolver/security.md` |
| Documentation parity | Replace legacy experimental docs with feature-owned record plus projections. | In progress | This feature record. |

## Known Gaps

- No phonetic or NLP matching is included.
- No cross-type resolution is supported.
- Operator-facing threshold guidance is minimal.
- False-positive and false-negative evaluation evidence is not yet recorded.
