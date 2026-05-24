# Plugin Publication Bootstrap — 2026-05-24

**Event type:** One-time API-token bootstrap publication
**Affected packages:** 6 security-sensitive plugins, all at version `0.9.0a8`
**Token:** `PYPI_BOOTSTRAP_TOKEN` (account-scoped, named
  `stigmem-plugin-bootstrap-2026-05-24`)
**Reason:** PyPI's Pending Trusted Publishers mechanism was non-functional
  in the maintainer environment.

## Affected artifacts

| Package | PyPI URL | First-publish workflow |
|---|---|---|
| `stigmem-plugin-memory-garden-acl` | https://pypi.org/project/stigmem-plugin-memory-garden-acl/ | bootstrap-publish-plugins.yml |
| `stigmem-plugin-source-attestation` | https://pypi.org/project/stigmem-plugin-source-attestation/ | bootstrap-publish-plugins.yml |
| `stigmem-plugin-multi-tenant` | https://pypi.org/project/stigmem-plugin-multi-tenant/ | bootstrap-publish-plugins.yml |
| `stigmem-plugin-tombstones` | https://pypi.org/project/stigmem-plugin-tombstones/ | bootstrap-publish-plugins.yml |
| `stigmem-plugin-time-travel` | https://pypi.org/project/stigmem-plugin-time-travel/ | bootstrap-publish-plugins.yml |
| `stigmem-plugin-lazy-instruction-discovery` | https://pypi.org/project/stigmem-plugin-lazy-instruction-discovery/ | bootstrap-publish-plugins.yml |

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
version of each affected plugin (e.g., `0.9.0a9` or `0.9.0a8.post1`) MUST
ship via the steady-state `publish.yml` OIDC path. The bootstrap workflow
file (`bootstrap-publish-plugins.yml`) is deleted before the next-version
publish to prevent accidental re-use.
