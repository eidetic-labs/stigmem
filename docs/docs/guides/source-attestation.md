---
id: source-attestation
title: Source Attestation
sidebar_label: Source Attestation
---

# Source Attestation

**Audience:** Node operators enforcing provenance guarantees on fact assertions.

:::info Coming soon
This guide covers Source Attestation (A2, ACM-76), a v0.9 addition. Spec draft is in progress.
:::

Source attestation binds a fact's `source` field to the caller's registered `entity_uri`. The node verifies that the asserted `source` matches the API key's registered identity.

Three modes:
- `enforce` — reject mismatched source claims with HTTP 403
- `warn` — accept and log; sets `attested: false` on the fact
- `off` — no verification (default in v0.8)

When shipped, this guide will cover configuration, key registration, and audit log integration.
