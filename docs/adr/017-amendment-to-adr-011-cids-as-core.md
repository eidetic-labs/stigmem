# ADR-017: Amendment to ADR-011 — CIDs as core (not plugin)

**Status:** Accepted
**Date:** 2026-05-07
**Authors:** Eidetic Labs
**Amends:** ADR-011 (C1 plugin architecture for cross-cutting features)
**Related:** ADR-003 (capability-based prompt-injection handling), ADR-016 (storage immutability enforcement); threat model R-23

---

## Context

ADR-011 (Accepted 2026-05-07) established a C1 plugin architecture for stigmem's cross-cutting features. Seven features were scoped as plugins, including content-addressed fact IDs (CIDs, §25). At the time of ADR-011's acceptance, CIDs were classified alongside other deferred features as opt-in plugin functionality — adopters who wanted cryptographic content addressing would install `stigmem-plugin-cids`.

Subsequent threat-modeling work revealed that this classification undervalues CIDs' role in stigmem's security architecture. Specifically:

1. **ADR-003's prompt-injection trust boundary depends on storage immutability** (per ADR-003 § Trust boundary). The L2 federation rule (no receiver-side promotion of `interpret_as`) assumes the storage `interpret_as` value is trustworthy.

2. **ADR-016 (storage immutability enforcement) commits CIDs as a load-bearing layer (L3)** in the defense-in-depth stack against R-23 (admin-level storage tampering). Without CIDs in core, ADR-016's L3 layer is opt-in and defense-in-depth has a hole.

3. **Federation peer integrity verification depends on CIDs.** Peers verify content integrity by recomputing CIDs from canonical bodies. If CIDs are an opt-in plugin, federation between deployments where one party has the plugin and the other doesn't has a degraded security posture — and detecting that asymmetry is itself a problem.

The original ADR-011 decision treated CIDs as orthogonal to the security architecture. ADR-016's analysis shows CIDs are load-bearing for both ADR-003 and the broader immutability story. Keeping CIDs as a plugin means:

- Default install lacks the integrity layer that backstops ADR-003 against storage compromise.
- Federation peer verification is conditional on plugin install, not architectural.
- Operators must understand that "default install" silently differs from "secure default install" by a critical layer.

This amendment corrects that.

## Decision

**Move CIDs from plugin scope to core scope.** Specifically:

1. CIDs are no longer one of the seven cross-cutting feature plugins per ADR-011.
2. CID generation, storage, and verification are part of stigmem core. Default install computes CIDs on every fact write and verifies CIDs on every fact read.
3. The other six cross-cutting feature plugins (lazy instruction discovery, time-travel, RTBF tombstones, memory garden advanced ACL, source attestation, multi-tenant) remain plugins per ADR-011's C1 architecture. **ADR-011's plugin model is otherwise unchanged.**

### What this changes in ADR-011's scope

| Feature | Original ADR-011 scope | Amended scope (this ADR) |
|---|---|---|
| Lazy instruction discovery | Plugin (`stigmem-plugin-lazy-instruction-discovery`) | Plugin (unchanged) |
| **CIDs (§25)** | **Plugin (`stigmem-plugin-cids`)** | **Core (not a plugin)** |
| Time-travel queries | Plugin | Plugin (unchanged) |
| RTBF tombstones | Plugin | Plugin (unchanged) |
| Memory-garden advanced ACL | Plugin | Plugin (unchanged) |
| Source attestation | Plugin | Plugin (unchanged) |
| Multi-tenant | Plugin | Plugin (unchanged) |

### What this changes in Phase A scope

- **PR 4b** (originally `stigmem-plugin-cids` implementation) becomes "implement CIDs as core feature" — same engineering work, different package boundary.
- The `stigmem-plugin-cids` package is not created.
- CID-related hooks (`pre_assert_transform` for CID generation, `federation_inbound_validate` for CID verification) move from plugin-registered to core-resident.
- The hook surface defined in ADR-011 § Hook surface table remains valid — `pre_assert_transform`, `federation_inbound_validate`, etc. — but core-resident handlers register them, not a plugin manifest.

### What this changes in default install behavior

Before this amendment:
- Default install: facts have no CID. `cid` field is null on stored rows. No content-addressed federation. Tamper detection requires installing the plugin.

After this amendment:
- Default install: every fact has a CID computed at write time. CID is a not-null required column. Content-addressed federation works out of the box. Tamper detection is on by default.

Operators cannot disable CIDs. There is no `STIGMEM_CIDS_ENABLED=false`. The CID is part of the fact identity.

## Alternatives considered

**1. Keep CIDs as a plugin but require it for federation deployments.** Considered. The argument: single-tenant non-federated deployments don't strictly need CIDs for ADR-003's trust boundary if there's no peer integrity story to protect. Rejected for two reasons: (a) ADR-016's L3 (CID-based tamper detection on read) is part of the storage immutability stack, which applies regardless of federation; (b) "default install minus plugin" being silently weaker than the documented spec is exactly the credibility-leak pattern stigmem should avoid post-retraction.

**2. Define a "secure-by-default" install variant that includes the CIDs plugin and a "lean install" variant that doesn't.** Rejected. Two install variants for the same project doubles the documentation, conformance testing, and adopter confusion. Worse, the lean variant has the worst marketing position imaginable: "this version of stigmem is less secure but smaller."

**3. Leave ADR-011 as-is; document the CIDs-required-for-security caveat in operator docs.** Rejected. Documentation cannot fix an architectural decision that puts the security floor below the spec's claims. Operators reading "facts are immutable" should not also need to read "...but only if you installed the plugin."

**4. Wait until ADR-016 is accepted before amending ADR-011.** Considered for sequencing. Both amendments could land together as a coherent set. Decided to draft them concurrently and accept them together (or as a coherent decision in the same sign-off batch). The substance of this amendment is independent of ADR-016's full implementation; CIDs being core matters whether or not the rest of ADR-016 lands.

## Consequences

### What gets easier

- **ADR-003's claims hold by default.** No "secure-only-if-plugin-installed" caveat.
- **ADR-016's L3 layer is universal.** Defense-in-depth is genuinely defense-in-depth, not optional.
- **Federation peer verification is unconditional.** Peers can always verify content integrity; no need to check whether the peer has the plugin.
- **Operator mental model simplifies.** The default install is the secure install.

### What gets harder

- **One fewer plugin to demonstrate the C1 pattern.** ADR-011's plugin architecture validates against the remaining six features. CIDs were the second priority (after lazy instruction discovery); now the second priority becomes time-travel. The pattern is still validated, just on a slightly different feature first.
- **Default install size grows slightly.** CID computation, the cid_aliases table, the migration. Marginal.
- **CID computation is on every write.** Performance cost: ~10-50μs per write for SHA-256 over the canonical body. Acceptable.

### New risks

- **R-AMD11-1: ADR-011's architectural commitment is weakened.** A reader of ADR-011 sees seven plugins; a reader of ADR-017 (this amendment) sees six plugins. Cross-references must be tracked. Mitigation: ADR-011 stays untouched (immutability rule); ADR-017 is the canonical statement of the six-plugin scope; future readers follow the chain via the `Amends:` reference.
- **R-AMD11-2: precedent for amending early-Accepted ADRs.** This is the first amendment to an Accepted ADR. It sets precedent: when a downstream ADR (here ADR-016) reveals a flaw in an upstream decision, amendment is the right move. Mitigation: amendments are infrequent and require the same sign-off as new ADRs; the precedent is appropriate, not concerning.

## Implementation plan

ADR-017 is a scope change, not a re-engineering effort. The actual CID work was already planned for Phase A PR 4b (per ADR-011). This amendment changes only:

- **Package boundary:** CID code lives in `node/src/stigmem_node/cid.py` (core), not in `experimental/cids/src/`.
- **Manifest:** no `stigmem-plugin-cids` package is created.
- **Hook registration:** `pre_assert_transform` and `federation_inbound_validate` for CIDs are core-resident; they register with the hook registry as part of node startup, not via plugin discovery.
- **Tests:** CID tests live in `node/tests/test_cids.py` (core), not in plugin tests.
- **Documentation:** CIDs are documented in `docs/Build/Concepts/Content-addressing` and `docs/Secure/Immutability-and-attestation` (per ADR-005 IA), not in `docs/Build/Plugins`.

### Cascade through master-checklist

- §4.5b PR 4b — rewrite from "implement `stigmem-plugin-cids`" to "implement CIDs as core feature."
- §4.5g multi-tenant — unchanged (still a plugin).
- Issue seed #49 — body updated to reflect CIDs as core.
- ADR-011's path mapping in §3.1 — unchanged (the file mapping is by ADR number, not feature).

### Cascade through ADR-011

ADR-011 is Accepted (immutable). It is **not** edited. This amendment is the canonical record of the scope change. Future readers of ADR-011 should be directed to ADR-017 via the ADR README index annotations and via the `Amends:` chain.

## Amendment process

This ADR may itself be amended per ADR-001 §Contributor approval rule (two contributors or the founder alone). Amendments to ADR-017 would, in turn, propagate back to ADR-011's effective scope.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*