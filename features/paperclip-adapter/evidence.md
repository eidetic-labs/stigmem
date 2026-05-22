# Paperclip Adapter Evidence

## Implementation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/paperclip-adapter/skill.md` | Paperclip company skill instructions for context reads, lifecycle writes, delegation handoff, and Python SDK usage. |
| `experimental/paperclip-adapter/emit-fact.js` | Node CLI helper for Stigmem `assert`, `query`, and `retract` API calls. |
| `experimental/paperclip-adapter/hook.sh` | Shell hook for checkout, complete, blocked, and post-tool-use heartbeat events. |
| `experimental/paperclip-adapter/concept.md` | Paperclip and Claude Code connector setup guidance. |
| `experimental/paperclip-adapter/concept-federation.md` | Federation integration guidance for Paperclip-managed fleets. |

## Test Evidence

No adapter-specific automated test suite is currently recorded. Minimal syntax
validation should cover:

```bash
bash -n experimental/paperclip-adapter/hook.sh
node --check experimental/paperclip-adapter/emit-fact.js
```

## Documentation Evidence

| Path | Evidence |
| --- | --- |
| `experimental/paperclip-adapter/README.md` | Adapter overview, setup, hook wiring, relation namespaces, and context pull pattern. |
| `experimental/paperclip-adapter/STATUS.md` | Legacy status pointer to this feature record. |
| `docs/docs/spec/adapter-abi.md` | Adapter ABI discussion includes Paperclip-style lifecycle facts. |
| `docs/docs/spec/namespace-registry.md` | Namespace registry includes `paperclip:` lifecycle facts. |

## Validation Commands

Use repository docs checks for feature-record and projection validation:

```bash
python3 scripts/check_feature_records.py
python3 scripts/check_feature_projections.py
python3 scripts/check_feature_security_projection.py
python3 scripts/check_feature_changelog_projection.py
python3 scripts/check_feature_compatibility_projection.py
python3 scripts/check_feature_protocol_projection.py
CHECK_SKIP_DOCS_INSTALL=1 bash scripts/check.sh docs
```

Use syntax checks for the implementation scripts:

```bash
bash -n experimental/paperclip-adapter/hook.sh
node --check experimental/paperclip-adapter/emit-fact.js
```

## Missing Evidence

- Live Paperclip harness validation is not complete.
- Hook behavior has not been covered by automated tests.
- CLI helper behavior has not been covered by mocked HTTP tests.
