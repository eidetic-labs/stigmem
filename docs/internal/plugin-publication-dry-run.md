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

> **Note (2026-05-24):** Hashes re-captured after correcting plugin versions
> from `0.9.0a8` (lock-stepped with stigmem-core, per PR #665's implicit
> alignment) to `0.1.0` (per-plugin independent versioning per ADR-011 and the
> amended publication contract). The original `0.9.0a8` artifacts were never
> published; this correction is pre-publication.

| Artifact | SHA-256 |
| --- | --- |
| `stigmem_plugin_lazy_instruction_discovery-0.1.0-py3-none-any.whl` | `24fc82f230989340ccdbdf8b7fd826e4005b2779050274906accdd3a039b1fa7` |
| `stigmem_plugin_memory_garden_acl-0.1.0-py3-none-any.whl` | `ab58efa4ddd227e40ae943d65ce87c17825be75be65bef2f116d4abc06f403f9` |
| `stigmem_plugin_multi_tenant-0.1.0-py3-none-any.whl` | `08833f67fbfc6b3eeb54c8db6ad1d7650eee37e92a54c5fb7d3cb56f8b9139cf` |
| `stigmem_plugin_source_attestation-0.1.0-py3-none-any.whl` | `5b315b8e323d806eaad20f738d03007c5b002e3db63f415e30a6119ce81ff2bc` |
| `stigmem_plugin_time_travel-0.1.0-py3-none-any.whl` | `0b218a883a9dad3afbddbceac1705438ed991e0bac5865153321f44513e446c7` |
| `stigmem_plugin_tombstones-0.1.0-py3-none-any.whl` | `f27cfdb5dd1830ec7f37507d4c4b7048b11662bafbd6d4bc5c01b30943a26452` |
| `stigmem_plugin_lazy_instruction_discovery-0.1.0.tar.gz` | `fc793ad5b5674de69d7fc231ee45aa94ad468b569ea9230e7e82e65017519d5e` |
| `stigmem_plugin_memory_garden_acl-0.1.0.tar.gz` | `7b07b47000c78bc2150134ad66e7118815a001821bbfcdf7b6f9c7309d4971d8` |
| `stigmem_plugin_multi_tenant-0.1.0.tar.gz` | `883ce1e6f1ca8f0c08338fa66b64e1e2ea950057a5a646e2910310b564f0c408` |
| `stigmem_plugin_source_attestation-0.1.0.tar.gz` | `ef9835eca34f7b211ab190fdd00fb71f0f42409733e5dc2a2e0bf8ceb087b675` |
| `stigmem_plugin_time_travel-0.1.0.tar.gz` | `597147022fb0730a989c9d885450c7c4c4242068c85a6a26086c1c2c7e932c04` |
| `stigmem_plugin_tombstones-0.1.0.tar.gz` | `114bdcb462dfccd31695b41fd9a425f231756681cc1ef308fb299871d6780431` |

## Registry and Release Disposition

No registry upload, release asset upload, GitHub release change, tag creation,
or signature/provenance publication occurred in this goal. A future publication
PR must record maintainer clearance, rerun clean-checkout build/install
verification, choose the target registry/channel, and document rollback or yank
instructions before any artifact is published.

The MCP adapter now has a separate npm dry-run record:
[`mcp-publication-dry-run.md`](mcp-publication-dry-run.md). It remains a
no-publication `hold` because explicit maintainer publication clearance is not
complete.
