# Time-Travel Queries Security

## Threat Model Delta

Time-travel adds a historical-read boundary to ordinary fact and recall reads.
Visibility is evaluated against a caller-provided timestamp rather than only
the current projection. That makes erased, expired, or legal-hold data handling
part of the security surface.

The plugin must treat `as_of` as an explicit elevated query mode. It must reuse
the same authentication, scope, garden, tombstone, CID, and
federation-integrity checks as current reads, then apply historical visibility
after those checks.

## Owned Risks

None currently identified. Time-travel does not own a standalone R-XX risk in
the current threat model.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-17 legal-hold historical data exposure | `as_of` reads are the mechanism that can expose pre-tombstone history when legal hold is active. | Non-admin callers cannot retrieve legal-hold history; preserved-data reads require admin handling and audit evidence. |
| R-18 CID field-exclusion tampering | Historical reads depend on metadata such as `valid_until` and source trust that are not CID identity fields. | Historical reads must not trust federated metadata changes that local validation would reject. |

## Operator Scenarios

- Keep the time-travel plugin disabled unless historical reads are an explicit
  operator requirement.
- Treat `as_of` access to legal-hold data as a compliance-sensitive admin
  action.
- Review audit trails before exporting or sharing historical query results.
- Do not accept federated metadata changes that extend `valid_until` beyond
  locally observed values.

## Conformance Pointers

Required adversarial vectors before promotion:

- default installs reject `as_of` queries when the plugin is not loaded;
- non-admin callers cannot retrieve legal-hold history through `as_of`;
- non-admin legal-hold suppression is indistinguishable from ordinary
  tombstone suppression in response bodies and count headers;
- time-travel reads exclude tombstoned data unless the caller is authorized for
  the legal-hold path;
- federation ingest rejects `valid_until` extension before historical reads can
  observe the fact;
- source-trust values used during historical reads are recomputed locally.

## Residual Risk

Gate 1 remains open for operator-facing legal-hold role separation, audit
runbooks, and federation authority validation. The a4 read-path coverage now
checks that historical reads do not bypass tombstone, legal-hold, CID, or
source-trust-style ranking controls.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
