# Plugin Publication Dry-Run

**Status:** complete for no-publication closeout
**Applies to:** plugin publication readiness Goal 5
**Last updated:** 2026-05-23

This record captures the Goal 5 dry-run result after the publication contract,
security-sensitive plugin readiness review, and adapter/tooling disposition
review landed.

No standalone plugin artifact is approved for registry publication in this
closeout. The six security-sensitive plugin source packages build locally, but
their feature records remain `hold` because publication still requires explicit
maintainer clearance. Adapter, tooling, dashboard, evaluation, and deployment
helper surfaces are either `hold` or `defer` per
[`plugin-publication-disposition.md`](plugin-publication-disposition.md).

## Publication Decision

| Surface group | Decision | Reason |
| --- | --- | --- |
| Security-sensitive plugins | Build dry-run complete; do not publish | Package builds pass, but maintainer publication clearance has not been granted. |
| MCP adapter | Do not publish | Classified `hold`; package alignment, live protocol smoke, adapter security certification, and npm dry-run evidence are complete, but host UI smoke and maintainer clearance remain open. |
| Obsidian adapter | Do not publish | Classified `hold`; live-vault smoke, packaging/channel ownership, and key-storage review remain open. |
| Partner/model adapters | Do not publish | Classified `defer`; ownership, live integration, and dependency validation remain open. |
| Dashboard, evaluation, deployment helpers | Do not publish | Classified `defer`; these are not standalone plugin publication targets for this milestone. |

## Dry-Run Commands

The following commands were run from the repository root. Output artifacts were
written under `/private/tmp/stigmem-plugin-goal5/` and were not committed,
published, signed, or uploaded.

```bash
uv build experimental/lazy-instruction-discovery --out-dir /private/tmp/stigmem-plugin-goal5/lazy-instruction-discovery
uv build experimental/time-travel --out-dir /private/tmp/stigmem-plugin-goal5/time-travel
uv build experimental/tombstones --out-dir /private/tmp/stigmem-plugin-goal5/tombstones
uv build experimental/memory-garden-acl --out-dir /private/tmp/stigmem-plugin-goal5/memory-garden-acl
uv build experimental/source-attestation --out-dir /private/tmp/stigmem-plugin-goal5/source-attestation
uv build experimental/multi-tenant --out-dir /private/tmp/stigmem-plugin-goal5/multi-tenant
```

## Dry-Run Hashes

| Artifact | SHA-256 |
| --- | --- |
| `stigmem_plugin_lazy_instruction_discovery-0.9.0a8-py3-none-any.whl` | `4f67b71e3ca31ff324dd2e17560cfe255c69662caaf72c23d17771363c20214e` |
| `stigmem_plugin_memory_garden_acl-0.9.0a8-py3-none-any.whl` | `c704efb5877f3379f95466e963b839fbafca007936f66b4d96c3eafac86ad7d7` |
| `stigmem_plugin_multi_tenant-0.9.0a8-py3-none-any.whl` | `b57ee2f8f94aa5d32f79af92144314299df6bb1b1f10776a1ad3c56376803bd5` |
| `stigmem_plugin_source_attestation-0.9.0a8-py3-none-any.whl` | `28f4c74e8e5c7f0e30d4492e5ba38e8a2d57090b27d478bfdbc8ed6f032a29ac` |
| `stigmem_plugin_time_travel-0.9.0a8-py3-none-any.whl` | `542662fd12620225a1c95854d717dfa98751f520ea1108709c214c27d289b262` |
| `stigmem_plugin_tombstones-0.9.0a8-py3-none-any.whl` | `4aa6795dd8c51d2c4362f2e79d4d15c6a0a167998fcd1f1975ca05debb6af365` |
| `stigmem_plugin_lazy_instruction_discovery-0.9.0a8.tar.gz` | `f252837d1a62025c7332494c4b0f1e5d63c0138d58c2b1779773d76c03fa76bf` |
| `stigmem_plugin_memory_garden_acl-0.9.0a8.tar.gz` | `69c2a3f6618a4f824a7741abd91fbb670d0794fc1847b8f63387921b4afe5b18` |
| `stigmem_plugin_multi_tenant-0.9.0a8.tar.gz` | `5156312429ffd35de5d0d634d34ed5477c137664787d133e9e69013746ed707d` |
| `stigmem_plugin_source_attestation-0.9.0a8.tar.gz` | `61a41aa34c6e8345134523068f1db11221206be89373b4ef798328d21ecdf211` |
| `stigmem_plugin_time_travel-0.9.0a8.tar.gz` | `7cc12aa887ff7b9f7b8c018132865b3c32d03a64aca9c677aa0e76509ce5412a` |
| `stigmem_plugin_tombstones-0.9.0a8.tar.gz` | `529a344e72d38ee6e42366516d20fd31780aacce8ba7abd853e77f01d220efd6` |

## Registry and Release Disposition

No registry upload, release asset upload, GitHub release change, tag creation,
or signature/provenance publication occurred in this goal. A future publication
PR must record maintainer clearance, rerun clean-checkout build/install
verification, choose the target registry/channel, and document rollback or yank
instructions before any artifact is published.

The MCP adapter now has a separate npm dry-run record:
[`mcp-publication-dry-run.md`](mcp-publication-dry-run.md). It remains a
no-publication `hold` because host UI smoke and explicit maintainer publication
clearance are not complete.
