---
title: Protocol Motivation
sidebar_label: Motivation
audience: Spec
description: "Stigmem protocol motivation — why immutable typed facts beat per-agent mutable stores."
---

# Protocol Motivation {#section-1}

**Status:** Protocol overview prose retained from the v0.9.0a1 specification lineage.

Why immutable typed facts beat per-agent mutable stores.

**Authoritative source:** [`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

Every agent, every human, and every company maintains its own private memory.
Facts decay silently, contradict each other across contexts, carry no provenance,
and cannot travel with the entity they describe.

Stigmem is the missing substrate: an open, federated knowledge fabric that any agent
or human can write facts into and query against, plus a typed intent/protocol layer
so agents can express goals, hand off work, and defer to each other without
designing bespoke handshake protocols every time.

Stigmem does **not** replace company orchestration platforms, agent runtimes, or tool
protocols like MCP. It sits above them all — the shared cognitive layer they can
all reason over.

---
