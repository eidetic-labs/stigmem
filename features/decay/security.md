# Decay Semantics Security

## Threat Model Delta

Decay changes fact availability and confidence over time. Misconfiguration can
either preserve stale facts too long or suppress useful facts too aggressively.
Because decay can affect recall output, it must respect tombstones,
legal-hold handling, scopes, system facts, and quota boundaries.

## Owned Risks

None currently identified.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-02 resource exhaustion | Sweeps can become expensive if triggered too often or across large scopes. | Keep rate limits and operator controls in place for sweep surfaces. |
| R-16 tombstone DoS | Decay must not revive, weaken, or hide tombstone suppression semantics. | Apply tombstone filtering independently of decay confidence updates. |

## Operator Scenarios

- Treat aggressive decay policies as availability-affecting configuration.
- Use dry-run before applying broad sweeps.
- Exclude system facts and legal-hold material from ordinary decay policies.

## Conformance Pointers

Required vectors before promotion:

- decay does not mutate system facts;
- dry-run produces no writes;
- scope-restricted sweeps do not affect other scopes;
- tombstoned entities remain suppressed regardless of decay state.

## Residual Risk

Decay should remain experimental until operator policy, tombstone interaction,
and broad-sweep behavior are validated under production-like loads.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
