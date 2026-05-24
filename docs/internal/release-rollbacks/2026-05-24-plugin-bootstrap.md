# Plugin Publication Bootstrap — 2026-05-24

**Event type:** One-time API-token bootstrap publication
**Affected packages:** 6 security-sensitive plugins, all at version `0.1.0`
**Token:** `PYPI_BOOTSTRAP_TOKEN` (account-scoped, named
  `stigmem-plugin-bootstrap-2026-05-24`)
**Reason:** PyPI's Pending Trusted Publishers mechanism was non-functional
  in the maintainer environment.

## Affected artifacts

| Package | First-publish version | PyPI URL |
|---|---|---|
| `stigmem-plugin-memory-garden-acl` | `0.1.0` | https://pypi.org/project/stigmem-plugin-memory-garden-acl/ |
| `stigmem-plugin-source-attestation` | `0.1.0` | https://pypi.org/project/stigmem-plugin-source-attestation/ |
| `stigmem-plugin-multi-tenant` | `0.1.0` | https://pypi.org/project/stigmem-plugin-multi-tenant/ |
| `stigmem-plugin-tombstones` | `0.1.0` | https://pypi.org/project/stigmem-plugin-tombstones/ |
| `stigmem-plugin-time-travel` | `0.1.0` | https://pypi.org/project/stigmem-plugin-time-travel/ |
| `stigmem-plugin-lazy-instruction-discovery` | `0.1.0` | https://pypi.org/project/stigmem-plugin-lazy-instruction-discovery/ |

## Version-correction note

This bootstrap publishes `0.1.0` for each plugin. An earlier proposal had
aligned plugin versions to `stigmem-core`'s `0.9.0a8` per PR #665's
interpretation of "version aligned to release train"; pre-publication review
identified that the contract intent was `requires_stigmem` alignment, not
version-string equality. The contract was amended and versions were corrected
to per-plugin independent values before the first publish event. No `0.9.0a8`
plugin artifacts were ever published to PyPI.

## Token lifecycle

- **Created:** 2026-05-24 by maintainer
- **Scope:** Entire account (required because target projects did not yet exist)
- **Bootstrap publication:** 2026-05-24 via
  `bootstrap-publish-plugins.yml`, run
  `26371777786` (`dry_run=false`)
- **Trusted Publisher configured per project:** 2026-05-24 by maintainer
- **PyPI bootstrap token revoked:** 2026-05-24 by maintainer
- **GitHub secret deleted:** 2026-05-24 by maintainer
- **Workflow file deleted:** 2026-05-24 in cleanup PR

## Published SHA-256 hashes

The real publish workflow verified these hashes against
`docs/internal/plugin-publication-dry-run.md` before upload. Post-publish
verification downloaded the published wheels and sdists from PyPI and confirmed
the same hashes.

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

## Post-publication verification

- Real publish workflow:
  https://github.com/eidetic-labs/stigmem/actions/runs/26371777786
- PyPI JSON returned `200` for all six packages at `0.1.0`.
- Published wheels and sdists were downloaded from PyPI and SHA-256 verified
  against this record and `docs/internal/plugin-publication-dry-run.md`.
- Trusted Publisher is configured for all six projects before the next
  release.
- `PYPI_BOOTSTRAP_TOKEN` was revoked in PyPI and deleted from GitHub secrets.

## Next-version protocol

After bootstrap completes + Trusted Publishers are configured, the next
version of each affected plugin (e.g., `0.1.1` or `0.2.0`) MUST
ship via the steady-state `publish.yml` OIDC path. The bootstrap workflow
file (`bootstrap-publish-plugins.yml`) is deleted before the next-version
publish to prevent accidental re-use.
