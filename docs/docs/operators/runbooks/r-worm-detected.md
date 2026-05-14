---
title: R-WORM-DETECTED
sidebar_label: R-WORM-DETECTED
description: Incident runbook for suspected automated cross-peer or agent-to-agent propagation.
audience: Operator
---

# R-WORM-DETECTED

Use this runbook when writes appear to propagate automatically through agents or
peers in a pattern that resembles a worm.

Trigger alert:

- `worm_pattern_detected`

Supporting signals:

- Agent-read and agent-write graphs mirror each other beyond baseline.
- Sudden instruction-like facts from peers that do not normally write them.
- Rapid growth in facts across multiple peer sources.
- Repeated quarantine admissions for similar payloads.

## Identify

Preserve the graph shape and affected payloads:

```bash
curl -s "https://your-node.example.com/v1/federation/audit?limit=500" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .

curl -s "https://your-node.example.com/v1/facts?limit=500" \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" | jq .
```

Record the first suspicious fact, the relation names involved, the peers that
sent or received related facts, and whether any agent-control or instruction
relations are present.

## Contain

1. Disable federation pulls from affected peers.
2. Stop or isolate agents that read from the affected scopes.
3. Disable automated quarantine promotion.
4. Tighten read/write quotas for affected principals.
5. If a connector or adapter is involved, disable that connector until payloads
   are reviewed.

Containment is intentionally broad. Restore access only after the propagation
path is understood.

## Investigate

Trace the propagation path:

- Which fact was read before each suspicious write?
- Which agent or peer wrote the next copy?
- Did the payload change as it moved?
- Did any fact ask an agent to fetch, write, or forward additional facts?
- Did the pattern cross organization boundaries?

Compare findings against
[Security Scenarios](../../security/scenarios.md), especially prompt-injection
and federation scenarios.

## Recover

1. Retract or quarantine malicious payloads.
2. Rotate any API keys used by affected agents.
3. Re-enable agents one at a time with lower quotas.
4. Re-enable federation one peer at a time.
5. Add a regression test or detection rule for the payload pattern if it is new.

## Communicate

Notify affected peer operators with the payload shape, timestamps, and
containment actions. If the incident crossed org boundaries, publish a short
public note after containment that states impact, affected versions, and
operator actions.
