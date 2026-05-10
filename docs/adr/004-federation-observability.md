# ADR-004: Federation observability and incident response

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** Threat model §22.3, R-19; `OPERATING.md`; ADR-002

---

## Context

In a federated system, the worst incidents are the ones that happen *between* nodes — a malicious peer pushing crafted HLC values, a compromised peer's signed manifest leaking, a worm propagating through cross-org handoffs. These incidents are not visible inside any single node's logs in a useful way; they are visible only when an operator can see the *federation graph* — what's flowing between nodes, who's writing how often, what the per-peer drift looks like.

The retracted v1.0 shipped with audit-event types defined in §22.3, but with several gaps relevant to federation:

- No explicit per-peer rate aggregation (which peer is writing how much, of what relation type).
- No drift-tracking events for HLC, capability-token timestamp, or quarantine-promotion latency.
- No defined severity/alert taxonomy — every event is at the same level.
- No incident-response runbooks naming what to do when specific signals fire.

Operators running federated stigmem deployments need a defined set of signals, a defined alert threshold for each, and a defined response. Without that, the audit log is forensics — you can reconstruct what happened after the fact, but you can't act in time.

This ADR defines the observability and incident-response surface for v1.0 federation. It is intentionally separate from the threat model (which says *what could go wrong*) and the audit-event taxonomy in §22.3 (which says *what we record*). This document says **what we monitor, alert on, and respond to**.

## Decision

We define three layers: signals, alerts, and runbooks.

### Layer 1: Signals (what we record)

Federation signals are a subset of audit events, plus derived metrics, named explicitly and emitted with structured fields suitable for SIEM ingestion.

**Per-peer connection signals:**
- `federation_connect`: peer entity URI, mTLS verification result, capability token presented.
- `federation_disconnect`: peer entity URI, reason (clean/abrupt/timeout).
- `federation_handshake_failed`: peer entity URI, failure reason (cert mismatch, expired token, manifest invalid).

**Per-peer activity signals:**
- `peer_fact_write`: peer entity URI, scope, relation, count (aggregated per minute).
- `peer_fact_read`: peer entity URI, scope, count (aggregated per minute).
- `peer_quarantine_admit`: peer entity URI, fact id, reason (always-quarantined-by-policy / interpret_as=instruction / low source trust).

**Drift signals:**
- `peer_hlc_anomaly`: peer entity URI, observed HLC, local HLC, drift seconds, threshold breached.
- `peer_replay_rejected`: peer entity URI, nonce, reason.
- `peer_capability_violation`: peer entity URI, attempted verb+object, granted scope.

**Quarantine signals:**
- `instruction_quarantined`: peer entity URI, fact id, age in queue.
- `instruction_promoted`: admin entity URI, fact id, time-to-promote.
- `quarantine_aged_out`: fact id (a fact that sat in quarantine longer than the configured retention).

**Manifest and key signals:**
- `manifest_rotation_observed`: peer entity URI, new key id, Rekor inclusion proof status.
- `manifest_rotation_failed`: peer entity URI, failure reason.
- `key_expiring_soon`: key id, days remaining (emitted at 30/14/7/1 day thresholds).
- `key_expired_blocked`: key id, attempted operation.

### Layer 2: Alerts (what fires when)

Each alert is defined with: name, severity, condition, default threshold, recommended response. Operators can tune thresholds in their deployment config.

| Alert | Severity | Condition | Default threshold |
|---|---|---|---|
| `peer_hlc_drift_high` | Warning | `peer_hlc_anomaly` events from a single peer | >5/hour |
| `peer_hlc_drift_critical` | Critical | drift in seconds | >300s in a single event |
| `peer_handshake_failure_burst` | Warning | `federation_handshake_failed` from a single peer | >3/minute |
| `peer_replay_burst` | Critical | `peer_replay_rejected` from a single peer | >5/hour |
| `peer_capability_violation` | Critical | any `peer_capability_violation` event | 1 |
| `quarantine_backlog` | Warning | facts in quarantine waiting for promotion | >50 facts or any aged >24h |
| `instruction_quarantined_unprecedented` | Warning | `instruction_quarantined` from a peer that has never written instruction-typed facts before | 1 |
| `manifest_rotation_failed` | Critical | any `manifest_rotation_failed` event | 1 |
| `key_expired_blocked` | Critical | any `key_expired_blocked` event | 1 |
| `worm_pattern_detected` | Critical | per-peer agent-write graph mirrors agent-read graph beyond baseline | (pattern-defined) |

Each alert maps to a runbook (Layer 3).

### Layer 3: Runbooks (what to do)

Every Critical alert must have a named runbook in `OPERATING.md` covering:

1. **Identify** — what data to gather first, what queries to run.
2. **Contain** — what to disable or revoke immediately to stop the bleeding.
3. **Investigate** — what audit-log queries reveal the scope of impact.
4. **Recover** — what to retract, rotate, or republish.
5. **Communicate** — federation peers to notify, what to post publicly if the project's reputation is implicated.

Initial runbooks shipped in v0.9.x:

- **R-PEER-COMPROMISE:** for `peer_capability_violation`, `peer_replay_burst`, suspicious manifest rotation.
- **R-WORM-DETECTED:** for `worm_pattern_detected` — coordinates with the OpenClaw allowlist defense and ADR-003 channel separation.
- **R-MANIFEST-FAILURE:** for `manifest_rotation_failed` — covers Rekor unavailability and signing-key compromise scenarios.
- **R-HLC-DRIFT:** for `peer_hlc_drift_critical` — covers honest-clock-skew vs. malicious-peer disambiguation.
- **R-KEY-EXPIRY:** for `key_expired_blocked` — recovery from a missed rotation.

## Alternatives considered

**1. Rely entirely on the existing audit log; let operators wire their own dashboards.** Rejected. "Roll your own observability" is a non-answer for the operator who's evaluating whether stigmem is deployable. The defining question for federation infrastructure is "how do I know when it's going wrong?", and the answer needs to be in our docs, not in their imagination.

**2. Ship a Grafana dashboard.** Considered; deferred. Per ADR-002, Grafana is an `experimental/` deferred feature. We define the signals and alerts in v1.0 and ship the Grafana dashboard in v2.0.0-experimental once one external operator has actually used it.

**3. Define richer ML-driven anomaly detection.** Rejected for v1.0. Threshold-based alerts are tractable, debuggable, and operator-tunable. Anomaly-detection ML is none of those things until you have enough deployment data to train against, which we don't.

**4. Skip runbooks; let operators figure it out.** Rejected. The most credible signal stigmem can give a prospective operator is "we've thought about what to do when X happens." Runbooks are that signal in concrete form.

## Consequences

### What gets easier

- **Operators have a defined operational posture.** "Subscribe to these alerts; follow these runbooks" is the answer to the question "how do I run this safely?"
- **Phase B operator soak has structured feedback.** The 30-day external operator runs against a known set of signals; their bug reports can reference signal names.
- **Threat-model risks have observability mappings.** R-19 (HLC manipulation) is observable via `peer_hlc_drift_critical`; R-21 (worm vector) is observable via `worm_pattern_detected`. The threat model and the operations manual cross-reference.
- **Public retro posts have telemetry.** When a real incident happens (and it will), the retro post can name the signal that fired, the runbook that ran, and the time-to-recovery.

### What gets harder

- **Signal stability is a contract.** Once we name `peer_hlc_anomaly` as a signal, we can't rename it without breaking operator dashboards. Wire format applies to telemetry too.
- **Runbook maintenance is real ongoing work.** Each runbook needs to be updated as the underlying mitigations evolve; out-of-date runbooks are worse than no runbooks.
- **Per-peer aggregation has a storage cost.** Peer rate aggregation needs sliding-window counters; configurable retention.

### New risks

- **R-OBS-1: alert fatigue.** Default thresholds tuned too sensitive will produce noise; operators stop reading alerts. Mitigation: ship defaults that produce zero alerts on a healthy single-org single-peer demo deployment; document tuning guidance per deployment shape.
- **R-OBS-2: runbook drift from reality.** A runbook that says "rotate the org signing key" when the procedure changes is worse than no runbook. Mitigation: every runbook is dated and linked from the corresponding code paths; updates are required as part of the PR that changes the code.

## Implementation plan

This ADR's implementation is split across multiple PR cycles in the strengthening plan, but lower priority than the security-critical work:

- **Phase B (federation hardening) (alongside audit-log work):** Signals layer — emit all named events with the defined structured fields.
- **Phase B (operator-facing work) (alongside OPERATING.md):** Runbook documents drafted with placeholder thresholds.
- **Phase B (operator soak begins) (during operator soak):** Tune thresholds based on operator feedback; refine runbooks with real incident data.

Alerts (Layer 2) are operator-side configuration; we publish recommended thresholds and example Prometheus alerting rules in `OPERATING.md`, but we don't run an alert pipeline as part of the node.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*