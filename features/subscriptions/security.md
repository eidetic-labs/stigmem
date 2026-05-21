# Subscriptions Security

## Threat Model Delta

Subscriptions add a long-lived event-delivery boundary. A caller can be
authorized when a subscription is created but lose access before an event is
delivered. The feature therefore must treat delivery-time authorization as the
security boundary, not creation-time authorization.

## Owned Risks

None currently identified. Subscription-specific risks are currently expressed
as contributions to existing capability-token and tombstone/security surfaces.

## Contributed Risks

| Risk | Contribution | Mitigation |
| --- | --- | --- |
| R-14 capability-token validation | Subscriptions require a `subscribe` verb and target-bound authorization. | Validate token verb/object before persistence and again before delivery. |
| R-16 tombstone DoS and suppression | Tombstones must suppress subscription delivery for covered entities. | Delivery code must filter event content through tombstone checks before outbound delivery. |

## Operator Scenarios

- Treat webhook destinations as data egress points.
- Rotate or revoke subscription credentials when garden membership changes.
- Keep replay windows short enough to avoid long-lived access leakage.

## Conformance Pointers

Required vectors before promotion:

- revoked capability tokens stop receiving event content;
- non-members do not receive garden-scoped event content;
- tombstoned entities do not appear in subscription payloads;
- webhook retries do not bypass authorization after access changes.

## Residual Risk

Subscriptions must not graduate until delivery-time authorization, replay
handling, and cancellation behavior are covered by conformance vectors.

## Advisories and Findings

No public GHSA is currently owned by this feature record.
