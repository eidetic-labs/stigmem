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
- **Bootstrap publication:** 2026-05-24 via `bootstrap-publish-plugins.yml` (run TBD)
- **Trusted Publisher configured per project:** 2026-05-24 (target)
- **Token revoked:** 2026-05-24 (target — within 24h of publication)
- **Workflow file deleted:** 2026-05-24 (target — same commit as token revocation)

## SHA-256 hashes (must match plugin-publication-dry-run.md)

(Populated automatically by the bootstrap workflow's verify step. If this
record is read post-publication and the hashes diverge from
`docs/internal/plugin-publication-dry-run.md`, that is a tamper signal —
investigate immediately.)

## Next-version protocol

After bootstrap completes + Trusted Publishers are configured, the next
version of each affected plugin (e.g., `0.1.1` or `0.2.0`) MUST
ship via the steady-state `publish.yml` OIDC path. The bootstrap workflow
file (`bootstrap-publish-plugins.yml`) is deleted before the next-version
publish to prevent accidental re-use.
