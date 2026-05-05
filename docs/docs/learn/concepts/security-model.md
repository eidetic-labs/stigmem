---
title: Security Model
sidebar_label: Security Model
description: Stigmem's security model — scopes, signing, federation trust, attestation, capability tokens, and the quarantine garden.
---

# Security Model

Stigmem's security model rests on five primitives that compose into the full trust story: **scopes**, **signing**, **federation trust**, **source attestation**, and **capability tokens**. Each is a small, well-defined piece — the strength of the model is in how they fit together.

## Scopes — the visibility boundary

Every fact is written with one of four scopes:

| Scope     | Visibility                                                                                  |
|-----------|---------------------------------------------------------------------------------------------|
| `local`   | Origin node only. Never federated under any circumstances.                                  |
| `team`    | Origin node only. Never federated under any circumstances.                                  |
| `company` | Federated only when the active `PeerDeclaration` explicitly includes `"company"` in `allowed_scopes`. |
| `public`  | Federated by default between registered peers.                                              |

Scope enforcement is **read- and write-time**. A misconfigured peer cannot escalate `team` facts to `public` because the scope is checked before the fact is admitted to the federation pipeline. See [§3.5](/docs/reference/spec) for the normative spec.

## Signing — Ed25519 over every cross-node payload

Every node publishes a `federation_pubkey` at `/.well-known/stigmem`. Cross-node primitives are signed with the corresponding private key:

- **PeerDeclaration** — JSON document signed by the declaring node (excluded fields enumerated in spec §6.2).
- **Federation cursor advances** — HLC cursor checkpoints carry signatures so a misbehaving peer cannot replay or rewrite history.
- **Capability tokens** (see below) — short-lived JWS signed by the scope owner.

Key rotation uses a **dual-trust window** — the previous and current keys are both accepted for a configurable overlap, then the previous key is revoked via the transparency log.

## Federation Trust — quarantine and source-trust scoring

Each cross-org write is admitted via a **source-trust score** `t ∈ [0,1]` derived from identity strength, peer history, scope authority, and attestation mode. Effective confidence at recall time is `confidence × t`.

Facts below a configurable trust threshold land in a **quarantine garden** for human review before entering the canonical fact store. The quarantine garden is itself a Memory Garden (§17) with admin-only ACL — operators triage, accept, or reject quarantined writes from a single dashboard.

Facts also accumulate `derived_from: [fact_hash...]` and `attestation_chain: [signature...]` for tamper-evident audit. See [Federation Trust](/docs/build/guides/federation-trust) for the operator runbook.

## Source Attestation — binding writes to identities

Source Attestation (spec §18) binds an `entity_uri` to an API key so every fact written by that key carries a verifiable `attested` field. Three enforcement modes:

| Mode      | Behaviour                                                                                    |
|-----------|---------------------------------------------------------------------------------------------|
| `enforce` | Reject unattested writes. Default for federated peers and the curator dashboard.             |
| `warn`    | Log unattested writes but admit them. Useful for migration windows.                          |
| `off`     | Disable attestation checking. Only appropriate for fully trusted single-tenant deployments.  |

Attestation is the **trust anchor for the connector ecosystem**: third-party integrations write under their own attested identity, and the curator dashboard can filter or quarantine by attestation.

## Capability Tokens — explicit, short-lived authority

Writing scope `S` on a peer node requires a short-lived **capability token** signed by the scope owner. Each capability carries an explicit subject + verb + object plus an expiry. Capabilities are revocable via the transparency log, and the receiving node verifies the chain at admission time.

The result: cross-org writes are **authorised**, not just authenticated. A leaked capability has a bounded blast radius (the verb/object pair) and a bounded lifetime (the expiry).

## How it fits together

A typical write path under the full security model:

1. The agent obtains a capability token from the scope owner (e.g. `subject: agent:writer-bot`, `verb: assert`, `object: scope:public:project:loom`, `exp: now+5m`).
2. The agent signs the request with its API key.
3. The receiving node verifies (a) the API-key signature, (b) the capability chain, (c) the source-trust score against the current threshold, and (d) the scope rules.
4. If trust ≥ threshold, the fact enters the canonical store with an `attested` chain.
5. If trust < threshold, the fact lands in the quarantine garden for admin review.
6. At recall time, effective confidence is `confidence × t` so low-trust facts are de-ranked even after admission.

## Reading on

- [Federation Trust guide](/docs/build/guides/federation-trust) — operator setup end-to-end.
- [Audit Log & Quotas](/docs/operate/security/audit-and-quotas) — what's logged, retention, and how to read the audit stream.
- [Key Rotation runbook](/docs/operate/runbooks/key-rotation) — dual-trust window mechanics.
- [Container Hardening](/docs/operate/security/container-hardening) — the deployment-side security posture.
- [Security Disclosure](/docs/community/security-disclosure) — reporting vulnerabilities responsibly.
