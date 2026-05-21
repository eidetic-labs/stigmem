# OIDC SSO Evidence

## Implementation

| Path | Purpose |
| --- | --- |
| `node/src/stigmem_node/routes/auth.py` | OIDC exchange, JWKS discovery/cache, token validation, domain allowlist enforcement, key rotation, and key-management routes. |
| `node/src/stigmem_node/settings.py` | OIDC settings and ID-token algorithm allowlist. |
| `node/src/stigmem_node/auth.py` | API-key storage, verification, identity resolution, and OIDC subject propagation. |
| `node/src/stigmem_node/models/auth.py` | OIDC exchange and key-management response models. |
| `node/src/stigmem_node/observability/audit_event.py` | Audit event propagation of `oidc_sub`. |

## Tests

| Evidence | Coverage |
| --- | --- |
| `node/tests/auth/test_oidc.py` | Disabled-state handling, discovery URL safety, unsafe JWKS rejection, token validation, algorithm allowlist, domain allowlist, permission ceiling, key listing/revocation, same-sub rotation, and response shape. |
| `node/tests/auth/test_identity.py` | `/v1/me` OIDC subject visibility and audit records carrying `oidc_sub`. |
| `node/tests/plugins/test_memory_garden_acl_plugin_validation.py` | Advanced ACL plugin gate for membership-derived OIDC permission ceilings. |

## Projection Checks

| Check | Coverage |
| --- | --- |
| `python3 scripts/check_feature_records.py` | Confirms the feature record is complete and aligned with the migration inventory. |
| `python3 scripts/check_feature_projections.py` | Confirms public feature and experimental indexes include migrated experimental records. |
| `python3 scripts/check_feature_changelog_projection.py` | Confirms root changelog projection links to feature-local history. |
| `python3 scripts/check_feature_compatibility_projection.py` | Confirms compatibility projection includes feature metadata. |
| `python3 scripts/check_feature_protocol_projection.py` | Confirms `canonical_spec: none` is explicitly represented in the feature spec. |

## Evidence Gaps

- No external IdP soak evidence is recorded in this feature record.
- No operator-specific runbook evidence exists for Okta, Auth0, Keycloak, or
  Microsoft Entra ID.
- No production support commitment is recorded for the alpha line.
