# Source and Test Decomposition Inventory

**Issue:** [#180](https://github.com/Eidetic-Labs/stigmem/issues/180)  
**Status:** Pre-rc planning tracker  
**Last updated:** 2026-05-15  
**Scope:** Post-plugin-extraction source/test decomposition work that should
complete before v1.0.0-rc.0, without blocking active PR 4 plugin work.

## Sequencing Decision

Plugin infrastructure PR 4-INF.1 through PR 4-INF.4 has landed. Cross-cutting
feature plugins are no longer expected to move large blocks of core route or
test code in a way that would conflict with the decomposition plan below.

Broad decomposition remains sequenced after plugin extraction. Focused
implementation PRs may still perform narrow local moves when a change needs
them, but the issues below are the planned refactor slices.

## Current Inventory

Line counts were taken from `main` on 2026-05-15 with:

```bash
find node/src node/tests eval adapters experimental \
  -path '*/node_modules' -prune -o \
  -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' \) \
  -print0 | xargs -0 wc -l | sort -nr | head -50
```

| Path | Lines | Classification | Proposed slice |
|---|---:|---|---|
| `node/tests/test_phase8_identity.py` | 1642 | Hard decomposition candidate | Split into `node/tests/identity/` by identity concern. |
| `node/tests/test_federation.py` | 1237 | Discouraged size | Split by federation concern. |
| `eval/federation/soak_driver.py` | 1189 | Discouraged size | Split into `eval/federation/soak/` phases. |
| `node/src/stigmem_node/routes/facts.py` | 1114 | Completed | Split into `routes/facts/` subpackage in #265; public import path preserved as `stigmem_node.routes.facts`. |
| `node/tests/test_phase10_instruction.py` | 1084 | Discouraged size | Defer until lazy instruction discovery rework; keep linked to experimental feature. |
| `node/src/stigmem_node/cli.py` | 1080 | Discouraged size | Split into `cli/` command-family modules. |
| `node/src/stigmem_node/routes/recall.py` | 1025 | Discouraged size | Split into `routes/recall/` stage modules. |
| `node/tests/test_tombstones.py` | 1024 | Discouraged size | Defer to tombstones experimental/plugin rework. |
| `node/src/stigmem_node/routes/federation.py` | 1009 | Discouraged size | Split into `routes/federation/` endpoint-family modules. |
| `node/src/stigmem_node/models.py` | 690 | Pydantic concentration | Split into domain modules before Phase C. |

Generated files and archived specs are excluded from this tracker. Files below
1000 lines can still be decomposed when they are high-churn, high-complexity,
or tightly coupled to one of the planned slices.

## Child Issue Plan

These issues are the focused slices for #180. Each child issue should link this
inventory, name validation commands, and avoid unrelated behavioral changes.

| Slice | Issue | Target | Validation gate |
|---|---|---|---|
| Pydantic models PR A | [#263](https://github.com/Eidetic-Labs/stigmem/issues/263) | Create `node/src/stigmem_node/models/` domain modules and a compatibility shim. | `uv run pytest node/tests -q --tb=short`; `uv run mypy node/src`. |
| Pydantic models PR B | [#262](https://github.com/Eidetic-Labs/stigmem/issues/262) | Move inline route wire-format models into domain modules. | Route tests for touched modules; OpenAPI contract check. |
| Pydantic models PR C | [#261](https://github.com/Eidetic-Labs/stigmem/issues/261) | Sweep imports to explicit domain paths and document shim retirement. | Full Python fast gate and changed-file quality gate. |
| CLI decomposition | [#264](https://github.com/Eidetic-Labs/stigmem/issues/264) | Split `node/src/stigmem_node/cli.py` into command-family modules. | CLI handler tests and generated CLI docs check. |
| Facts route decomposition | [#265](https://github.com/Eidetic-Labs/stigmem/issues/265) | Split `routes/facts.py` into endpoint/helper modules. | Fact route tests, CID/provenance tests, OpenAPI check. |
| Federation route decomposition | [#266](https://github.com/Eidetic-Labs/stigmem/issues/266) | Split `routes/federation.py` by endpoint family. | Federation, mTLS, capability, and conformance tests. |
| Recall route decomposition | [#268](https://github.com/Eidetic-Labs/stigmem/issues/268) | Split `routes/recall.py` by lexical/vector/graph/ranking stages. | Recall, embeddings, vector search, and graph tests. |
| Identity test decomposition | [#267](https://github.com/Eidetic-Labs/stigmem/issues/267) | Split `test_phase8_identity.py` into `node/tests/identity/`. | Identity/key/capability tests; no fixture behavior changes. |
| Federation test decomposition | [#269](https://github.com/Eidetic-Labs/stigmem/issues/269) | Split `test_federation.py` by federation concern. | Federation test subset; conformance smoke. |
| Federation soak driver decomposition | [#270](https://github.com/Eidetic-Labs/stigmem/issues/270) | Split `eval/federation/soak_driver.py` into setup/run/monitor/report modules. | Eval soak import smoke and existing eval fast subset. |

## Deferrals

- `node/tests/test_phase10_instruction.py` belongs with lazy instruction
  discovery redesign rather than a standalone Phase B refactor.
- `node/tests/test_tombstones.py` belongs with tombstone experimental/plugin
  rework rather than a standalone Phase B refactor.
- `node/src/stigmem_node/routes/instruction.py` stays deferred with lazy
  instruction discovery unless an implementation PR requires a local cleanup.

## Compatibility Shim Retirement

The `stigmem_node.models` package remains a backwards-compatible re-export
surface after the Pydantic decomposition. Internal code should import from
explicit domain modules such as `stigmem_node.models.facts` or
`stigmem_node.models.tombstones`; a dedicated compatibility smoke test keeps
the historical broad import path working for external consumers.

Do not add a runtime deprecation warning to `stigmem_node.models` during the
pre-rc import sweep. Per ADR-013, deprecating a public API surface requires a
release-scoped deprecation PR with replacement guidance and release artifacts.
The earliest appropriate retirement point for the compatibility shim is a
future major-version deprecation/removal cycle after v1.0.0 GA.

## Tracking Notes

- Parent: [#180](https://github.com/Eidetic-Labs/stigmem/issues/180)
- Phase B parent: [#165](https://github.com/Eidetic-Labs/stigmem/issues/165)
- Evidence tracker: [#158](https://github.com/Eidetic-Labs/stigmem/issues/158)
- #264 implementation converts `stigmem_node.cli` from a monolithic module to
  a package while preserving the public `stigmem_node.cli` import and
  `python -m stigmem_node.cli` entry point.
- #265 implementation converts `stigmem_node.routes.facts` from a monolithic
  module to a route subpackage while preserving the public
  `stigmem_node.routes.facts` import path and existing route registration.
