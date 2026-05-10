# ADR-007: Argon2id migration for API key hashing

**Status:** Accepted
**Date:** 2026-05-06
**Authors:** Eidetic Labs
**Related:** Threat model §4 Assumption #2, T1-S1, R-03; `stigmem-security-revisions.md` P0-4

---

## Context

The v1.0 release documented API key storage as "Argon2id-hashed at rest." The implementation used SHA-256 (`hashlib.sha256` in `auth.py`). The discrepancy was identified during the Rev 2.0 threat-model update.

The Rev 2.0 threat model resolved the discrepancy by updating the documentation to match the code — keeping SHA-256 with the rationale that UUID4-derived keys carry sufficient entropy to make offline brute-force infeasible regardless of hash speed.

On further review, this argument has three weaknesses:

1. **UUID4 produces 122 bits of entropy, not 128.** Six bits are reserved for version and variant fields. Minor in absolute terms; the documentation should be precise, and an argument that depends on entropy counts deserves correctness in those counts.

2. **The argument assumes every key, forever, is properly UUID4-derived.** The moment a future change introduces test keys, custom-format keys, manually-issued keys, or backwards-compatibility shims with weaker entropy, SHA-256 silently provides no protection. The threat model has to be re-litigated on every key-format change. Argon2id remains correct under all such changes.

3. **Defense-in-depth.** When a database breach exposes 1,000 hashed API keys, an attacker can attempt cracking adjacent keys at near-zero marginal cost with SHA-256. Argon2id makes that cost real (target tuning: ~250ms per attempt on 2GB memory). For a database breach scenario, this is the difference between "all keys are now compromised" and "the attacker can crack maybe the 5 weakest before we rotate."

Argon2id is the [OWASP-recommended](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html) password-hashing function and the modern industry default. Its parameters (memory, time, parallelism) are tunable to deployment constraints. Library support in Python is mature (`argon2-cffi`).

Switching to Argon2id is a known-good upgrade with minimal operational cost, and avoids the structural dependency on key-format invariants.

## Decision

We migrate API key storage from SHA-256 to Argon2id. The migration uses dual-mode verification during a transition window so existing keys continue to work without forced rotation.

### Hash parameters

We adopt the [OWASP recommended baseline](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#argon2id):

- **Algorithm:** Argon2id (the variant resistant to both side-channel and time-memory tradeoff attacks).
- **Memory cost:** 19 MiB (`m_cost=19456`).
- **Time cost:** 2 iterations (`t_cost=2`).
- **Parallelism:** 1 lane (`parallelism=1`).
- **Salt:** 16 random bytes per key, stored alongside the hash.
- **Hash output:** 32 bytes.

These parameters are tuned to ~50ms per verification on a typical server CPU, which is the right balance of attack-resistance and operational latency for an API-key check on every request.

### Storage format

Hashes are stored in the canonical Argon2 encoded format:

```
$argon2id$v=19$m=19456,t=2,p=1$<base64 salt>$<base64 hash>
```

The format encodes the algorithm and parameters, allowing future parameter upgrades without a separate version field.

### Migration: dual-mode verification

For the duration of v0.9.x, the auth module supports verifying keys against either hash format:

```python
def verify_api_key(presented_key: str, stored_hash: str) -> bool:
 if stored_hash.startswith("$argon2id$"):
 return argon2.verify(presented_key, stored_hash)
 elif looks_like_sha256(stored_hash):
 # Legacy: verify against SHA-256, then opportunistically re-hash with Argon2id
 if hmac.compare_digest(sha256(presented_key), stored_hash):
 background_rehash(presented_key) # Re-hash and update the row
 return True
 return False
 else:
 raise InvalidHashFormat()
```

Existing keys verify against SHA-256 on first use, then are opportunistically re-hashed with Argon2id and the database row is updated. Keys not used during the v0.9.x window remain in SHA-256 form; v1.0.0 stable adds a one-time bulk re-hash migration that processes any remaining SHA-256 hashes by issuing forced rotations (the keys must re-authenticate to receive their re-hashed form).

### New key issuance

From v0.9.x onward, all newly issued keys are hashed with Argon2id. The existing UUID4-based key generation (122-bit entropy) is preserved — Argon2id strengthens the storage; the high-entropy generation remains the primary defense.

### Verification of the migration

A new audit event `api_key_rehashed` fires every time a legacy SHA-256 key is opportunistically re-hashed. Operators can query the audit log to see the migration progress:

```sql
SELECT COUNT(*) FROM audit_events WHERE event_type = 'api_key_rehashed'
```

When this count equals the number of SHA-256 hashes remaining in the keys table, the migration is complete for that key (it has been used and re-hashed).

## Alternatives considered

**1. Stay on SHA-256; document the random-token-only invariant.** Considered. This was option B in `stigmem-security-revisions.md` P0-4. For uniformly random, server-generated UUID4-style tokens, SHA-256 verification material can be defensible: the practical attack is not "crack a human password," it is "guess a high-entropy bearer token." Rejected anyway because that defense depends on a permanent key-generation invariant that future integrations can accidentally weaken. Argon2id is not a substitute for high-entropy token generation; it is defense-in-depth that keeps the storage layer correct if custom key formats, migration shims, or operator-provided keys are introduced later.

**2. Use bcrypt or scrypt instead of Argon2id.** Rejected. Argon2id won the [Password Hashing Competition](https://www.password-hashing.net/) explicitly because it improves on bcrypt and scrypt's tradeoffs. There's no reason to prefer the older algorithms unless a specific dependency forbids Argon2id.

**3. Use HMAC-SHA256 with a node-side secret instead of a slow hash.** Rejected. HMAC defeats offline brute-force when the secret stays secret, but the secret is stored on the same disk as the database — any attacker who can read the database can read the secret. HMAC adds operational complexity without meaningfully changing the threat model.

**4. Forced rotation of all keys on the v0.9.x release.** Rejected. Forces every operator to re-issue every API key on upgrade, breaking integrations. Dual-mode verification with opportunistic re-hashing is operationally smoother.

**5. Higher Argon2id parameters (more memory, more iterations).** Considered. Higher parameters increase attacker cost but also increase verification latency on every authenticated request. The chosen parameters are OWASP-recommended for password hashing; we can revisit upward if benchmarks show ample headroom.

## Consequences

### What gets easier

- **Threat-model assumption matches code.** §4 Assumption #2 in the threat model can be rewritten without the entropy-dependent "UUID4 entropy makes SHA-256 fine" argument.
- **R-03 fully closes.** API key max-age is already enforced (per Phase 12); now the at-rest hashing also matches industry standard. T1-S1's residual narrows to "key revocation must still be performed manually on suspected compromise" — which is a much smaller residual.
- **Future key-format changes are safe.** If we ever introduce shorter test keys, custom-prefix keys, or any non-UUID4 key format, the storage layer remains correct.
- **Adopters with security-review processes have a clean answer.** "Argon2id with OWASP-recommended parameters" is a sentence security teams expect to see; "SHA-256 because UUID entropy" is a sentence that triggers follow-up questions.

### What gets harder

- **Latency on first authenticated request.** Argon2id verification adds ~50ms versus SHA-256's microseconds. For an API where every request is authenticated, this is meaningful — but it's the right cost for the security gain.
- **Migration logic is dual-mode for one minor version.** Slightly more complex auth code during v0.9.x; simplifies in v1.0.0 once the bulk re-hash completes.
- **Memory footprint per verification.** 19 MiB per Argon2id verification means concurrent auth load has a real memory cost. At 100 concurrent authentications, that's 1.9 GB transient. Mitigation: rate limits (R-02 mitigated) cap concurrent auth volume; for high-throughput deployments, the parameters can be tuned downward with documented tradeoffs.

### New risks

- **R-A2ID-1: parameter rot.** OWASP recommendations evolve as hardware improves. Argon2id parameters that are correct in 2026 may need increasing in 2030. Mitigation: parameters are encoded in the hash format; re-hash on parameter upgrade is the same code path as the SHA-256 → Argon2id migration. Schedule parameter review every 2 years.
- **R-A2ID-2: argon2-cffi vulnerability.** A CVE in the underlying library would affect every authenticated request. Mitigation: Dependabot alerts on the dependency; library is widely used and well-maintained.
- **R-A2ID-3: opportunistic re-hash race.** Two concurrent verifications of the same legacy SHA-256 key could both trigger re-hash. Mitigation: re-hash uses a row-level lock; second attempt is a no-op.

## Implementation plan

Targeted for v0.9.x (alongside the Phase B (federation hardening) federation hardening).

- Add `argon2-cffi` to `pyproject.toml` dependencies.
- Update `auth.py` with dual-mode verification per the spec above.
- Add `api_key_rehashed` audit event type.
- Update threat model §4 Assumption #2 with the new language (per security-revisions P0-4).
- Update T1-S1 in the STRIDE table.
- Update OPERATING.md with the migration story for operators upgrading from v1.0 (now superseded by v0.9.0-preview) and from earlier v0.9.x.
- Add benchmark tests confirming verification latency stays under 100ms p99 with the chosen parameters.

For v1.0.0:
- Add bulk re-hash migration that handles any remaining SHA-256 keys by forcing a rotation.
- Remove the SHA-256 verification path from `auth.py`.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*