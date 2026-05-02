---
id: index
title: Specification (v0.2)
sidebar_label: Overview
---

# Stigmem Specification v0.2

:::note
This is the **v0.2** specification — the first public draft. For the current spec see [v0.5](/docs/spec).
:::

v0.2 is the foundation spec. Key concepts introduced:

- **Atomic Fact Shape** — `(entity, relation, value, source, confidence, scope, valid_until?)`
- **FactValue types** — string, number, boolean, null, **text** (new in v0.2), datetime, ref
- **Reification** — N-ary relationships via `loom:rel:<uuid>` prefix (renamed `stigmem:rel:` in v0.5)
- **Intent Envelope** — goal, constraint, preference, deference, escalation, handoff
- **Wire Format** — POST/GET `/v1/facts`, GET `/.well-known/stigmem`
- **Federation sketch** — handshake described but not fully specified (promoted to full spec in v0.5)

The authoritative source is `stigmem/spec/stigmem-spec-v0.2.md` in the repository.
