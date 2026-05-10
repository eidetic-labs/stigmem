# ADR-016: Storage immutability enforcement

**Status:** Accepted
**Date:** 2026-05-07
**Authors:** Eidetic Labs
**Related:** ADR-001 (versioning), ADR-003 (capability-based prompt-injection handling — load-bearing dependency on storage immutability), ADR-011 (C1 plugin architecture), ADR-017 (amendment to ADR-011 moving CIDs back to core); threat model R-09 (audit log integrity), **R-23 (admin-level storage tampering)**

---

## Context

Stigmem's spec repeatedly claims that facts are immutable: "A fact is **immutable once written**. Updates are new facts." (`spec/stigmem-spec-v0.7-draft.md` §2 and onward.) This claim appears in §2, §3 (retraction), §17 (memory garden), §18 (source attestation), and is referenced in ADR-003 as load-bearing for the prompt-injection trust boundary.

A code audit reveals the claim is structurally unsupported. The `facts` table in `node/migrations/001_init.sql` has no triggers, no permission denials, and no other mechanism preventing UPDATE or DELETE. Application code in `node/src/stigmem_node/` issues `UPDATE facts` in at least seven distinct places (decay sweep, vector search backfill, CID backfill, recall pipeline, quarantine, gardens). Immutability is by convention only, and the convention is already partially violated by core paths.

This is not just a technical-debt issue. **ADR-003's prompt-injection trust boundary depends on storage immutability.** The L2 rule (federation cannot promote `interpret_as` on replication) assumes the storage `interpret_as` value is trustworthy. If an attacker can mutate facts in place — change `value_v` to malicious payloads, change `interpret_as` from `content` to `instruction` — ADR-003's structural defenses are bypassed by the storage compromise, not by federation. The recall pipeline reads the mutated fact and serves it through the `instructions` channel; the adapter renders it as legitimate instruction; the LLM executes.

The threat scenario that sharpens this:

> A malicious actor with admin-level privileges on a stigmem node (via supply-chain compromise, credential theft, insider threat, or operator error) overwrites existing facts with malicious instruction payloads. The mutated facts are served through stigmem's federated recall path to consuming LLM agents, executing data exfiltration or arbitrary commands on host infrastructure.

Captured as **R-23: admin-level storage tampering / fact mutation attack** in the threat-model deltas.

This is a credible threat that local enforcement alone cannot defeat: an attacker with admin privileges controls the database, the application code, the migrations, the file system, and the verifier. **Every layer that lives entirely on the compromised node is theoretically bypassable.** The only durable defense is anchoring fact integrity to evidence the attacker does not control.

This ADR commits to a defense-in-depth stack that addresses R-23 as well as the realistic non-admin threats (application bugs, privileged-but-not-malicious users, federated peer integrity verification).

## Decision

Adopt a four-layer immutability stack as the v1.0 baseline. Each layer defends against a distinct threat class; combined, they make tampering detectable even under admin compromise.

### Layer 1 (L1): Architectural — append-only journal + projection tables

The `facts` table becomes append-only by application architecture. Mutating paths are refactored to write to projection tables that are explicitly mutable, while the source-of-truth `facts` table accepts only INSERT.

Concretely:

- **`facts` table:** insert-only. No application code path issues UPDATE or DELETE on this table.
- **New projection tables for the seven existing mutation paths:**
  - `fact_validity_overrides` — decay sweep target (was `UPDATE facts SET valid_until`).
  - `fact_embedding_status` — embedding cache (was `UPDATE facts SET embedding_missing`).
  - `fact_recall_signals` — recall pipeline materialized signals (was `UPDATE facts ...` from recall_pipeline.py).
  - `fact_cid_backfill` — CID assignment table (was `UPDATE facts SET cid` from cli.py).
  - `fact_quarantine_status` — quarantine state (was `UPDATE facts ...` from quarantine.py).
  - `fact_garden_membership` — garden assignment (was `UPDATE facts ...` from gardens.py).
- **Read path changes:** queries against `facts` join projection tables for derived state. Recall pipeline returns fact + projections.
- **Retraction model unchanged:** retraction stays as a new fact assertion per spec; the retraction *event* lands in `fact_retractions` (already append-only per the comment in `routes/facts.py:171`).

This is a substantive refactor. ~1-2 weeks, touches every read path and every mutation site. Eliminates the entire class of accidental-mutation bugs.

### Layer 2 (L2): SQLite engine — triggers blocking UPDATE/DELETE

```sql
CREATE TRIGGER facts_no_update
    BEFORE UPDATE ON facts
    BEGIN SELECT RAISE(ABORT, 'facts are append-only (ADR-016)'); END;

CREATE TRIGGER facts_no_delete
    BEFORE DELETE ON facts
    BEGIN SELECT RAISE(ABORT, 'facts are append-only (ADR-016)'); END;
```

These triggers are added in a new migration. They catch any code path that goes around L1's discipline — application bugs, contributor mistakes, third-party library interactions. They do not defeat an admin-level attacker (who can `DROP TRIGGER` or edit the database file directly), but they raise the cost and make non-admin tampering immediately visible.

Audit events: `fact_mutation_attempted` fires on trigger activation. Operators monitor this; non-zero counts are anomalous.

### Layer 3 (L3): Per-record cryptographic integrity — content-addressed fact IDs

Every fact carries a CID (per spec §25): a hash computed deterministically over the fact's canonical body. On read, the CID is recomputed and compared. Tamper detection:

- If `value_v` or any other CID-covered field is mutated post-insert, the recomputed CID does not match the stored CID. Read path returns an integrity error.
- The CID is included in the fact when it federates to peers. Peers can recompute CIDs from the canonical body and compare.
- Federation operates on CIDs, not opaque IDs — peers verify content matches expectations.

**This requires moving CIDs from a plugin (per ADR-011 C1 architecture) back to core.** ADR-017 (separate amendment to ADR-011) commits to that move. CIDs are no longer an opt-in feature; they are part of the v1.0 critical path because R-23 mitigation depends on them.

The CID computation covers: `entity`, `relation`, `value_type`, `value_v`, `source`, `timestamp`, **`interpret_as`** (added per ADR-003), `scope`. Mutation of any of these by an attacker breaks the CID — including the critical case of changing `interpret_as` from `content` to `instruction`.

### Layer 4 (L4): Hash chain — local sequence-level integrity

A `fact_chain` table records a hash chain over fact insert events:

```
chain_index  | fact_cid                  | prev_chain_hash | this_chain_hash
0            | <CID of first fact>       | (genesis)       | h(genesis || cid_0)
1            | <CID of second fact>      | h(genesis|cid_0)| h(prev || cid_1)
...
```

Each new fact append produces a new chain entry. Sequence tampering (removal, reordering, insertion at an arbitrary point) breaks the chain at the tampered index.

Per-read overhead: optional verification — clients can request the chain proof for a returned fact and verify it locally. Not all reads require verification; cross-org / federated reads should verify by default.

**L4 is included in v1.0** because it pairs with L5 cleanly (the chain checkpoints are what get committed to the external witness).

### Layer 5 (L5): External transparency log — Sigstore Rekor anchor

The crucial layer for R-23. Stigmem commits chain checkpoints (every Nth fact, or at minimum every minute under sustained writes) to Sigstore Rekor or an equivalent transparency log:

- Each checkpoint includes the chain hash at that index, the chain index, and the timestamp.
- Rekor's append-only log is operated independently. The stigmem node operator does not control it.
- The Rekor log is itself transparency-logged and witnessed by external parties (Sigstore's network of monitors).

If an attacker with admin privileges on the stigmem node mutates facts and rewrites the local chain, the chain checkpoints they produce after rewriting will not match the Rekor entries committed before the attack. Anyone — peers, auditors, clients — comparing local state to Rekor sees the divergence immediately.

The attacker cannot:
- Modify Rekor entries previously committed.
- Make Rekor "forget" entries.
- Backdate new Rekor entries.

The attacker can:
- Continue serving consistent local lies until someone checks against Rekor. Mitigated by mandatory verification on cross-org / federated reads, and by clients independently fetching Rekor inclusion proofs.

L5 is what makes the immutability claim durable against R-23. Without L5, every other layer is in principle bypassable by a sufficiently privileged attacker.

### Client / peer verification (the part that operationalizes L5)

Recall responses include, in addition to the fact body:
- The fact's CID.
- The chain proof (chain_index, prev_chain_hash, this_chain_hash) for the fact's chain entry.
- The Rekor inclusion proof for the most recent checkpoint covering this fact's chain index.

Clients (SDK or adapter) verify all three before treating the fact as trusted:
1. Recompute CID from fact body; check it matches.
2. Recompute chain hash for the fact's chain entry; check it links correctly.
3. Verify Rekor inclusion proof against Rekor's known root.

Federation peers do this verification automatically on inbound replication. Clients can opt in via a `Stigmem-Verify: full` header (per ADR-012's `Stigmem-Version` model).

**Without client/peer verification, L5 provides no defense in practice.** This is the most-overlooked part of transparency-log architectures: the witness is only useful if someone checks it.

### Optional: hardware enforcement (deployment-specific, documented)

For adopters with regulatory requirements (HIPAA, SOX, FedRAMP, regulated finance), additional hardware-level immutability options are documented but not required:

- **WORM storage** (AWS S3 Object Lock, write-once disks): hardware-level append-only enforcement. Even root cannot overwrite. Recommended for any deployment where the threat model includes "operator may be compromised."
- **TEE / enclave execution** (SGX, AMD SEV, ARM TrustZone): code runs in a protected boundary the host OS cannot reach. Substantially harder for admin-level attackers to compromise.
- **HSM-backed signing** for chain checkpoints: keys cannot be extracted even by privileged users. Strengthens L4.

These are deployment options. Stigmem core ships compatibly with them but does not require them.

## Alternatives considered

**1. Local enforcement only (L1 + L2; skip L3, L4, L5).** Rejected for v1.0. Defends against application bugs and non-admin threats but provides no defense against R-23. The spec claims facts are immutable; without external attestation, that claim is unsupportable against admin-level attackers.

**2. Cryptographic per-record only (L3; skip chain and external witness).** Rejected. CIDs catch content tampering but not removal or whole-table rewrites. An attacker with admin privileges mutates a fact and recomputes the CID locally; the local view is consistent. Without sequence-level integrity (L4) or external anchoring (L5), CIDs alone don't defeat R-23.

**3. Local chain only (L4; skip external witness).** Rejected. A local hash chain is rewritable by an attacker with admin privileges. Without an external party who saw earlier checkpoints, the rewrite is undetectable. L4 needs L5 to be meaningful against R-23.

**4. Defer immutability to v2.0; document the gap in LIMITATIONS.md.** Rejected. ADR-003's prompt-injection defenses have already been accepted with the assumption that storage is immutable. Deferring immutability means ADR-003's claims are aspirational, not architecturally enforced. The retraction of v1.0 was caused by exactly this kind of mismatch between claim and reality. We should not ship v1.0 with the same pattern.

**5. Use a different external transparency log (not Sigstore Rekor).** Considered. Rekor is the most mature option, has external witnesses, has a Python SDK, and has growing adoption in supply-chain security. Alternatives (Certificate Transparency Logs, custom append-only logs run by a trusted third party) have weaker witness properties or fewer integrations. Rekor is the right choice; the architecture is generic enough to swap if needed.

**6. Use a blockchain instead of a transparency log.** Rejected. Blockchain consensus is overkill: stigmem doesn't need decentralized writes, just tamper-evident audit. Operating costs of blockchain integration far exceed Rekor for the same security property. Reconsider in v3.0+ if the federation model evolves toward fully trustless consensus.

**7. Require WORM storage as the default.** Rejected for v1.0. WORM storage adds adopter friction (special hardware or cloud configuration) without addressing the threat model proportionally — a Rekor-anchored chain provides similar tamper-detection properties without requiring specific storage hardware. WORM remains a documented deployment option for adopters with stronger threat models.

## Consequences

### What gets easier

- **The "facts are immutable" claim becomes architecturally enforceable.** L1+L2 catches bugs and accidents; L3 catches content tampering; L4+L5 catch admin-level tampering.
- **R-23 mitigation is structural, not procedural.** Operators don't need to trust admin discipline; the architecture itself constrains what an admin-level attacker can silently do.
- **ADR-003's trust boundary holds against storage compromise.** The `interpret_as` field is part of the CID; mutating it breaks integrity. The L2 federation rule (no receiver-side promotion) is now backstopped by L3 storage tamper-detection.
- **Federation peers can independently verify.** No need to trust a peer's claim about a fact's content; CIDs + chain proofs let any peer verify against Rekor.
- **Audit log integrity (R-09) gets the same treatment.** The audit log can use the same chain + Rekor pattern; this ADR establishes the pattern for facts and audit logs alike.
- **Compliance posture improves.** Tamper-evident audit with external attestation is the standard for HIPAA, SOX, FedRAMP, and regulated finance. Stigmem becomes credible for those workloads.

### What gets harder

- **Phase B timeline grows.** L1 (~1-2 weeks), L2 (~3 days), L3 (~1 week if CIDs are already specified, plus the ADR-017 amendment), L4 (~2 weeks), L5 (~2-3 weeks for Rekor integration + verification on read paths), client/peer verification (~1 week). Total: ~6-9 additional weeks added to Phase B.
- **Application refactor is real.** Seven existing mutation paths get redesigned around projection tables. ~10 files touched, comprehensive test coverage required to verify behavioral parity.
- **Read-path overhead.** Every read with verification costs CID recomputation + chain hash verification + Rekor inclusion proof verification. Acceptable for federated cross-org reads (which should always verify); optional for trusted-local reads.
- **Operator complexity.** Rekor key management, witness availability, retention policy, monitoring of `fact_mutation_attempted` events. Documented in `docs/Operate/Hardening` and `docs/Secure/Immutability-and-attestation`.
- **Storage growth.** Chain table grows monotonically; Rekor entries cost (Sigstore is free for OSS, but rate-limited at high volumes). Operators planning very-high-write deployments need to size accordingly.

### New risks

- **R-IMM-1: Rekor unavailable at write time.** If Rekor is down, the chain checkpoint can't be committed. Mitigation: writes proceed locally; checkpoints commit asynchronously with retry; operators alerted on sustained unavailability. The fact is still locally chained; it's the external witness that's delayed.
- **R-IMM-2: client doesn't verify.** A naive client that doesn't check CIDs / chains / Rekor proofs gets no security benefit from L3-L5. Mitigation: verification is on-by-default in the official SDKs; `Stigmem-Verify: full` is the documented best practice; non-verifying clients are explicitly called out as accepting their own risk.
- **R-IMM-3: Rekor compromise.** If Sigstore's Rekor is itself compromised, L5's integrity guarantee weakens. Mitigation: Rekor is itself transparency-logged and witnessed by external monitors; a Rekor compromise is detectable. Stigmem can also support multiple-witness submissions (commit checkpoints to multiple independent transparency logs) for the strongest threat models.
- **R-IMM-4: chain rebuild on legitimate operations.** Some legitimate operations (storage backend migration, deployment restoration from backup) need to rebuild the chain. Mitigation: backup-and-restore is an explicit operator runbook; chain rebuild requires re-anchoring to Rekor with explicit operator action; the new anchor establishes a new chain root with a documented event.
- **R-IMM-5: projection table drift.** Projection tables can be mutated by application bugs that affect derived state (e.g., decay validity overrides). Mitigation: projection tables are not the immutable source of truth; their drift is recoverable by replaying writes from the journal. Document explicitly that projection tables are mutable derived state.
- **R-IMM-6: WORM storage adoption gap.** Adopters in regulated workloads that *should* use WORM may not. Mitigation: operator hardening guide explicitly recommends WORM for regulated workloads; checked at the operator soak (Phase B exit per ADR-002) for at least one regulated-workload soak operator if available.

## Implementation plan

### Phase B sequencing

The immutability stack lands in Phase B. Sequenced to minimize parallel risk:

**B.1: ADR-017 amendment to ADR-011 (move CIDs to core).** ~1 day. Lands first because it changes the plugin scope of CIDs.

**B.2: L1 architectural refactor.** ~1-2 weeks. Adds projection tables; refactors all seven mutation paths. CI gate: every existing test passes against the new architecture; new property test verifies `facts` table only ever sees INSERT.

**B.3: L2 SQLite triggers.** ~3 days. New migration. CI gate: triggers are exercised by negative tests (try to UPDATE; expect error).

**B.4: L3 CID enforcement.** ~1 week. Per the spec §25 design (already specified). Verification at read time. CI gate: tampering test mutates a fact's `value_v` directly via SQL; recall returns integrity error.

**B.5: L4 hash chain.** ~2 weeks. New `fact_chain` table; chain computation on every fact insert; chain proof in recall responses. CI gate: chain rewrite test (manually rewrite chain; verify detection).

**B.6: L5 Rekor integration.** ~2-3 weeks.
- Rekor SDK integration in node.
- Checkpoint commit on every Nth fact or every 60 seconds (whichever first).
- Rekor inclusion proof in recall responses.
- Rekor verification helper in SDK.
- Operator runbook for Rekor unavailability.

**B.7: Client/peer verification.** ~1 week.
- Verification helpers in Python SDK.
- Federation inbound automatic verification.
- `Stigmem-Verify` header support per ADR-012.

**B.8: Operator hardening doc.** ~3-5 days. Lands in `docs/Operate/Hardening` and `docs/Secure/Immutability-and-attestation` per ADR-005 IA.

**Total Phase B addition:** ~6-9 weeks.

### Cross-references

- ADR-003 §Trust boundary explicitly notes that storage immutability is a precondition; ADR-016 satisfies that precondition. No ADR-003 amendment needed.
- ADR-011 amendment via ADR-017 (CIDs to core). Does not invalidate ADR-011's plugin architecture for the other six features.
- ADR-014 (compatibility matrix) gains a feature row for "storage immutability" with required versions.
- Threat model R-23 added (separate document update in `stigmem/security/threat-model-new-entries.md`).

## Open questions

- **What's the right Rekor checkpoint cadence?** Every Nth fact vs. time-based vs. size-based. Recommend: every 1000 facts OR every 60 seconds, whichever first. Reconsider with real-world write-load data from operator soak.
- **Should non-federation single-tenant deployments require Rekor?** Default: yes, but with `STIGMEM_REKOR_REQUIRED=false` operator override that disables L5 (with loud warning). Single-tenant deployments without an external threat model can choose to skip L5 if their threat model justifies it. Reconsider after operator soak feedback.
- **Witness diversity for very-high-assurance deployments?** Multiple-witness commit (Rekor + an additional transparency log) — defer to v1.x as an opt-in feature.

## Amendment process

Changes to this ADR require sign-off per ADR-001 §Contributor approval rule (two contributors or the founder alone). Common amendment cases:

- Changing the layer composition (e.g., dropping a layer).
- Changing the witness service away from Rekor.
- Changing default verification posture (verify-by-default vs. opt-in).
- Adding hardware enforcement requirements at the protocol level.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*