# Fuzzy Resolver Security

## Security Posture

Fuzzy resolver is an authenticated read and alias-management surface. It can
affect which entity a caller chooses for later queries or writes, so alias
creation and deletion must remain permission-gated and auditable through normal
node controls.

## Threat Model Deltas

| Risk | Current mitigation |
| --- | --- |
| Entity-existence disclosure | The entity-resolution route requires read permission before inspecting the live fact graph. |
| Alias poisoning | User alias registration is authenticated; migration-managed aliases cannot be deleted through the user alias API. |
| False-positive resolution | Layer 3 returns candidates with scores instead of mutating facts or silently rewriting stored entities. |
| Cross-type confusion | Layer 3 only searches entities with the same informal type prefix. |

## Advisories and Findings

No public GHSA is currently owned by this feature record.

## Security Gaps

- No feature-specific rate limit is documented for resolver scans.
- No formal false-positive tolerance or review workflow exists for production
  alias creation.
- Alias-management audit expectations need to be made explicit before the
  feature can be considered stable.
