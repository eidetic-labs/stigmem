# Stigmem Threat Model

**Revision:** 1.0 — Phase 12 (2026-05-04)
**Status:** Under review by design office.
**Applies to:** Stigmem v1.1-draft and reference node implementation.
**Spec cross-reference:** §19 (Federation Trust), §20 (Recall & Graph), §22 (Security Hardening).

---

## 1. Purpose and Scope

This document is the first formal threat model for the Stigmem reference node and federated protocol. It covers:

- The system architecture and component diagram.
- Trust boundaries and actors.
- STRIDE analysis per trust boundary.
- A risk register linked to spec sections and the Phase 12 hardening backlog.

It does **not** replace the operational [Security & Pen Testing guide](../../docs/docs/security/pen-test.md) or the project's [SECURITY.md](../../SECURITY.md). Those documents address disclosure policy, scope for community pen testing, and the current patched-CVE posture. This document addresses protocol-level and architecture-level threats.

---

## 2. System Architecture

### 2.1 Components

| Component | Description | Trust level |
|---|---|---|
| **Reference node** (Python/FastAPI) | HTTP API, federation layer, recall pipeline, MCP adapter, OpenClaw adapter | Server |
| **Storage backend** | SQLite, libSQL (Turso), or PostgreSQL; persists facts, embeddings, vector index, audit log, nonce cache | Local to node or cloud (libSQL cloud) |
| **Transparency log** | Rekor / Sigstore-equivalent for org manifest rotation events | External, append-only |
| **Org manifest** | Ed25519 keypair, entity-URI list, rotation events; served at `/.well-known/stigmem-manifest.json` | Node-published, public |
| **Capability tokens** | Short-lived signed tokens authorising cross-org writes (Ed25519, max 90 days) | Issued by node admin |
| **Peer node** | Another Stigmem node in a federation; may be operated by a different organisation | External, authenticated via mTLS + manifest |
| **MCP adapter** | Exposes `assert_fact`, `query_facts`, `recall`, `lint_scope` tools to MCP-compatible LLM runtimes | Trusted by node as a caller |
| **OpenClaw / Claude Code adapter** | Read/write memory paths for Claude Code integration | Trusted by node as a caller |
| **Obsidian adapter** | CLI/daemon or Obsidian plugin; bidirectional vault ↔ node sync | Local trusted client |
| **Admin client** | Human operator or automation holding an admin-scope API key | Privileged |
| **Agent / end client** | Automated agent or application holding a scoped API key | Semi-trusted; scope-limited |
| **Quarantine garden** | Isolated fact store for untrusted incoming federation writes pending human review | Internal |
| **Recall pipeline** | Three-stage hybrid (lexical + dense vector + graph) recall; embedding model (local or cloud) | Internal + optional external |
| **Embedding service** | nomic-embed-text-v1.5 (offline default) or cloud provider (opt-in) | External opt-in |

### 2.2 System Diagram

```
                          ┌─────────────────────────────────────────────┐
                          │              PUBLIC INTERNET                 │
                          │                                              │
          ┌───────────────┼──────────────┐      ┌───────────────────────┼────┐
          │  Agent/Client │              │      │  Peer Node B          │    │
          │  (API key)    │              │      │  (mTLS + capability   │    │
          └──────┬────────┘              │      │   token, §19 manifest)│    │
                 │ TB-1                  │      └────────────┬──────────┘    │
                 │ HTTPS (TLS 1.3)       │                   │ TB-2          │
                 ▼                       │                   │ mTLS (§22.1)  │
    ┌────────────────────────────────┐   │                   ▼               │
    │       Stigmem Reference Node  │   │    ┌──────────────────────────┐   │
    │                                │   │    │   Transparency Log       │   │
    │  ┌─────────────────────────┐   │   │    │   (Rekor / Sigstore)     │   │
    │  │   HTTP API (FastAPI)    │◄──┼───┘    │   TB-5 (HTTPS)          │   │
    │  │   /v1/*                 │   │        └──────────────────────────┘   │
    │  └──────────┬──────────────┘   │                                       │
    │             │                  │        ┌──────────────────────────┐   │
    │  ┌──────────▼──────────────┐   │        │  Embedding Service       │   │
    │  │   Recall Pipeline       │   │        │  (cloud opt-in)          │   │
    │  │   (lexical+vec+graph)   │   │        │  TB-8 (HTTPS)            │   │
    │  └──────────┬──────────────┘   │        └──────────────────────────┘   │
    │             │                  │                                        │
    │  ┌──────────▼──────────────┐   │                                        │
    │  │   Storage Backend       │   │  ┌─────────────────────────────────┐  │
    │  │   (SQLite/libSQL/PG)    │   │  │  Obsidian Adapter               │  │
    │  │   TB-4                  │   │  │  (CLI daemon or plugin)         │  │
    │  └─────────────────────────┘   │  │  TB-6 (localhost or HTTPS)      │  │
    │                                │  └────────────────┬────────────────┘  │
    │  ┌─────────────────────────┐   │                   │                   │
    │  │  MCP / OpenClaw Adapter │   │                   │                   │
    │  │  TB-3                   │◄──┼───────────────────┘                   │
    │  └─────────────────────────┘   │                                       │
    │                                │  ┌──────────────────────────────────┐ │
    │  ┌─────────────────────────┐   │  │  Admin Client                    │ │
    │  │  Quarantine Garden      │   │  │  (admin API key)                 │ │
    │  └─────────────────────────┘   │  │  TB-7                            │ │
    └────────────────────────────────┘  └──────────────────────────────────┘ │
                                                                              │
                          └─────────────────────────────────────────────────-┘
```

### 2.3 Trust Boundaries

| ID | Boundary | From | To | Authentication |
|---|---|---|---|---|
| **TB-1** | Internet → Node API | Agents, end clients | Node HTTP API | API key (Argon2id hashed) + TLS 1.3 |
| **TB-2** | Node ↔ Peer node | Federation replication | HTTP API on peer | mTLS (§22.1) + Ed25519 capability tokens (§19.3) |
| **TB-3** | Agent tool → Node | MCP / OpenClaw adapter | Node HTTP API | API key; tool call may carry adversarial content |
| **TB-4** | Node → Storage | Node process | DB file / libSQL / PG | Local filesystem or network (libSQL cloud) |
| **TB-5** | Node → Transparency log | Node | Rekor / Sigstore | TLS + Rekor API key (when used) |
| **TB-6** | Obsidian adapter → Node | Local plugin or CLI | Node HTTP API | API key stored in plugin config |
| **TB-7** | Admin → Node | Human / automation | Node admin API | Admin-scope API key |
| **TB-8** | Recall pipeline → Embedding | Node | Cloud embedding provider | Provider API key (opt-in only) |

---

## 3. Actors

| Actor | Description | Trust level |
|---|---|---|
| **Authenticated agent** | Holds a scoped API key; may call `assert_fact`, `query_facts`, `recall` within granted scope | Semi-trusted |
| **Admin operator** | Holds an admin API key; full control over keys, manifests, quarantine, quotas | Trusted |
| **Peer node** | Federation partner; authenticated via mTLS + capability token; write authority is scope-limited by the token | Conditionally trusted |
| **Obsidian plugin** | Local process with user-granted API key; same trust as authenticated agent | Semi-trusted |
| **Transparency log** | Append-only external service; provides verifiable audit of manifest rotations | Trusted read-only verifier |
| **LLM runtime** | Consumes recalled facts via MCP / OpenClaw adapter; may be prompt-injected | Untrusted content source |
| **External attacker** | Unauthenticated or credential-holding adversary attempting exploitation | Untrusted |

---

## 4. Assumptions

1. **Key confidentiality:** Ed25519 private signing keys are generated and stored on the operator's infrastructure. If a node signing key is compromised, the adversary can issue arbitrary capability tokens and org manifests. Key rotation (§22.2) and transparency log publication are the recovery mechanisms.
2. **API key storage:** API keys are Argon2id-hashed at rest. Plaintext API keys are visible only at issuance time. Compromised keys must be revoked and rotated via the admin API.
3. **mTLS as the federation transport:** TB-2 analysis assumes §22.1 mTLS deployment. Pre-§22.1 deployments (TLS only, no client cert) have a weaker peer-authentication posture; R-01 applies.
4. **SQLite at-rest encryption is opt-in (SQLCipher).** The default deployment does not encrypt the fact store at rest. Operators in regulated environments must enable SQLCipher explicitly.
5. **Recall sanitizer is best-effort:** The recall-time content sanitizer (§19.7) strips known prompt-injection sentinels, but cannot exhaustively detect all injection patterns in stored `value` fields.
6. **Cloud embedding is opt-in:** Fact content is not sent to external embedding services unless `STIGMEM_EMBED_MODEL_PROVIDER=openai` (or equivalent) is explicitly set.
7. **Transparency log availability:** §19.2 requires Rekor / Sigstore for org manifest verification. If the transparency log is unavailable, the node operates in a degraded verification mode (see §19.2.6 failure-closed behavior).
8. **Operator physical security:** The threat model assumes the node host is under operator control and not physically accessible to attackers. Physical access is out of scope.

---

## 5. Out of Scope

- Vulnerabilities in the static documentation site (`docs.stigmem.dev`) — no user data, no dynamic server-side logic.
- Attacks on third-party dependencies (libSQL cloud/Turso, PostgreSQL, Rekor) — report to upstream.
- Social engineering or phishing.
- Operator errors that bypass documented configuration controls (e.g., running as root, disabling TLS).
- Protocol-level weaknesses in Rekor or Sigstore itself.
- Physical server access.
- Rate-limiting / resource exhaustion scenarios with no clear security exploit path (tracked separately as availability concerns).

---

## 6. STRIDE Analysis

### 6.1 TB-1 — Internet / Agent → Node HTTP API

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T1-S1 | API key theft | Spoofing | Attacker obtains a leaked API key and impersonates a legitimate agent | Argon2id hashing at rest; keys visible only at issuance | Key rotation not enforced (R-03); no max-age |
| T1-S2 | Unauthenticated endpoint access | Spoofing | Attacker reaches write endpoints without a valid key | All write endpoints require `Authorization` header | — |
| T1-T1 | Tampered fact payload | Tampering | Attacker replays or modifies a fact assertion with a stolen key | Facts are scoped; replay of old payloads creates duplicate, auditable facts | No per-request integrity seal beyond TLS |
| T1-R1 | Missing read audit trail | Repudiation | Agent reads sensitive-scope facts; no record of what was returned | Audit log (§22.3) — `fact_read` event type | Audit log is Phase 12 delivery; not yet in v1.0-rc |
| T1-I1 | Cross-scope data leak via recall | Info. disclosure | Attacker uses a `public`-scoped key to reach `local` or `team` facts via the recall pipeline | Stage 2 ANN filter enforces scope (§20.3.3); garden ACL pre-filter at Stage 3 (§20.3.3) | Fuzz coverage of scope-isolation paths incomplete |
| T1-D1 | Resource exhaustion via recall | Denial of service | Attacker submits expensive graph-traversal recalls in a tight loop | Per-principal quotas (§22.4) | Phase 12; not enforced in v1.0-rc (R-02) |
| T1-D2 | Vector store disk exhaustion | Denial of service | Attacker asserts millions of facts via a compromised key, filling the embedding index | `fact_write` quota dimension (§22.4.2) | Phase 12; not enforced in v1.0-rc |
| T1-E1 | Elevated-scope key misuse | Elevation of privilege | Agent with `team` scope writes to `local` scope or admin scope | Scope enforcement at API layer (§3.5) | — |

### 6.2 TB-2 — Node ↔ Peer Node (Federation)

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T2-S1 | Peer impersonation | Spoofing | Attacker acts as a legitimate peer node, injecting facts | mTLS mutual cert verification (§22.1); SAN ↔ entity_uri binding | Pre-§22.1 deployments lack mTLS (R-01) |
| T2-S2 | Org manifest spoofing | Spoofing | Attacker publishes a fraudulent manifest under a legitimate entity URI | Ed25519 signature on manifest; Rekor inclusion proof check (§19.2.6) | Rekor check is failure-closed but service may be unavailable |
| T2-T1 | Replay attack on capability token | Tampering | Attacker replays a previously valid capability token to write facts | Nonce + timestamp window ±5 min (§22.5.2); persistent nonce cache | Nonce cache survives restarts per §22.5.2; fuzz coverage (R-06) |
| T2-T2 | HLC cursor manipulation | Tampering | Malicious peer sends crafted HLC values to push the local HLC forward | HLC implementation clamps skew | No independent validation of peer HLC claims |
| T2-R1 | Unreported federation events | Repudiation | Federation connect/disconnect events not logged | `federation_connect` audit event (§22.3.1) | Phase 12 audit log; not yet in v1.0-rc |
| T2-I1 | Cross-org scope leakage | Info. disclosure | Peer node reads facts beyond its capability token scope | Capability token verb/object validation (§19.3.3) | Partial: §22 amendments strengthen admission checks |
| T2-D1 | Replication queue flooding | Denial of service | Malicious peer sends a flood of replication requests | `federation_pull` quota (§22.4.2) | Phase 12 |
| T2-E1 | Excessive-scope capability token | Elevation of privilege | Token with wildcard or overly broad scope grants unwanted write authority | Token verb/object validation at admission; `subscribe` verb added to enum (§19.3.2) | Validator must reject scope claims not in token body (R-14) |

### 6.3 TB-3 — Agent Tool → Node (MCP / OpenClaw Adapter)

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T3-S1 | Indirect prompt injection | Spoofing | Adversarial content stored as a fact value is recalled and injects instructions into the LLM's context | Recall-time sanitizer strips known sentinels (§19.7) | Sanitizer is best-effort; novel injection patterns may bypass it (R-05) |
| T3-T1 | Entity URI injection | Tampering | Agent passes an unvalidated entity URI that triggers unexpected scope resolution | Pydantic validation at the API layer; URI format enforced | No semantic validation of URI namespace against agent's scope |
| T3-R1 | Tool calls unattributed | Repudiation | MCP tool calls not tied to a specific agent identity in the audit log | `fact_write` and `fact_read` audit events include `actor_entity` | API key must correctly identify the agent; shared keys lose attribution |
| T3-I1 | Cross-scope recall via tool | Info. disclosure | Agent exploits the recall pipeline to retrieve facts outside its granted scope | Scope enforcement at recall pipeline (§20.3.3) | Same as T1-I1 |
| T3-D1 | Recall loop via tool | Denial of service | Agent triggers expensive recalls in a loop (e.g., via prompt injection instructing it to recall repeatedly) | Per-agent quotas (§22.4) | Phase 12 |
| T3-E1 | Tool surface exposed to admin scope | Elevation of privilege | Agent tool configured with an admin-scope API key, giving the LLM full admin authority | No technical control — requires operator configuration discipline | Operator education; least-privilege key issuance |

### 6.4 TB-4 — Node → Storage Backend

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T4-T1 | SQLite WAL corruption | Tampering | Attacker with filesystem access corrupts the WAL to alter facts silently | WAL checkpointing integrity; signed snapshots (§22 backup) | Node process must detect and refuse to serve corrupted data |
| T4-T2 | libSQL cloud MITM | Tampering | MITM on the Turso/libSQL cloud connection alters stored facts | TLS to libSQL cloud endpoint | No additional integrity seal beyond TLS at the application layer |
| T4-I1 | At-rest data exposure | Info. disclosure | Attacker with disk access reads the unencrypted SQLite file | SQLCipher at-rest encryption (opt-in only) | Default deployment stores facts in plaintext at rest (R-04) |
| T4-I2 | Cloud backend data residency | Info. disclosure | Facts stored in libSQL cloud may be subject to cloud provider data access | Operator-configured Turso account; Turso's data residency controls apply | No additional Stigmem-layer encryption of fact payloads |
| T4-D1 | Vector store growth (no cap) | Denial of service | Unbounded embedding index growth exhausts disk | `fact_write` quotas (§22.4.2) | Phase 12; no eviction policy in v1.0-rc |

### 6.5 TB-5 — Node → Transparency Log (Rekor)

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T5-S1 | TLS cert spoofing on Rekor endpoint | Spoofing | Attacker intercepts the Rekor HTTPS connection to serve a fraudulent log | Standard TLS cert validation; Rekor log consistency checks (Merkle tree) | — |
| T5-T1 | Tampered log entry | Tampering | Attacker alters a submitted Rekor entry | Rekor's Merkle tree and inclusion proofs; `inclusion_proof_invalid` error (§19.2.6) | — |
| T5-R1 | Rotation events not logged | Repudiation | Node rotates org manifest without submitting a transparency log entry | §22.2.3 requires a `key_rotation` log entry on every rotation | Not enforced in v1.0-rc; Phase 12 delivery (R-10) |
| T5-D1 | Rekor unavailability blocks operations | Denial of service | Rekor outage prevents manifest verification, blocking federation | Failure-closed behavior in §19.2.6 (`transparency_log_unavailable` 503) | Operational; operators should monitor Rekor availability |

### 6.6 TB-6 — Obsidian Adapter → Node

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T6-S1 | API key in plaintext settings | Spoofing | Obsidian plugin settings file contains the API key in plaintext; other plugins may read it | Obsidian settings are local to the user's device | Key compromise requires local filesystem access (R-07) |
| T6-T1 | Vault file tampering via adapter | Tampering | Adapter writes unexpected changes back to vault files without user awareness | Conflict surfacing via Obsidian markdown comments; user reviews conflicts | Automated sync may overwrite user edits if conflict detection fails |
| T6-R1 | Sync operations not fully logged | Repudiation | Adapter performs bulk sync without recording which facts were written | `fact_write` audit events on the node side | Adapter itself has no persistent sync log |
| T6-I1 | Plugin reads full vault | Info. disclosure | Plugin holds read access to all vault notes, not just those in the configured sync folder | Scope configuration in plugin settings; enforcement is local | No technical scope enforcement at the filesystem level |
| T6-D1 | Retry storms on partition | Denial of service | Network partition causes adapter to flood the node with retry requests | Exponential backoff in adapter | No per-adapter quota dimension; covered by `fact_write` quota |
| T6-E1 | Plugin settings exposed to other plugins | Elevation of privilege | Malicious Obsidian plugin reads the Stigmem API key from settings | Obsidian settings are user-local; no cross-plugin isolation guarantee | Operator education; rotate key if another plugin is suspected |

### 6.7 TB-7 — Admin → Node

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T7-S1 | Admin key compromise | Spoofing | Attacker obtains an admin API key, gaining full node control | Admin key is Argon2id-hashed at rest | No enforced key max-age (R-03); key rotation not automated |
| T7-T1 | Malicious manifest publish | Tampering | Admin key used to publish a fraudulent org manifest | Manifest signature checked before publish | Compromised admin key can produce a validly-signed fraudulent manifest |
| T7-R1 | Admin operations not separately logged | Repudiation | Admin API calls not in a separate audit trail | `admin_action` audit event type (§22.3.1) | Phase 12 audit log |
| T7-D1 | Quota abuse via admin key | Denial of service | Admin key bypasses principal quotas, enabling self-DoS | Admin quota dimension ceilings apply (§22.4) | Admin may override quota policies by design |

### 6.8 TB-8 — Node → Cloud Embedding Service (opt-in)

| # | Threat | Class | Description | Existing control | Residual risk |
|---|---|---|---|---|---|
| T8-S1 | Embedding provider API key exposed | Spoofing | Provider API key in environment config is leaked | Key stored in env var (not committed to source) | Rotation requires redeployment (R-13) |
| T8-T1 | Poisoned embeddings | Tampering | Cloud provider returns adversarially crafted embeddings to manipulate recall ranking | Not controlled at the node layer | No integrity check on returned embedding vectors |
| T8-I1 | Fact content sent to external service | Info. disclosure | Every `"{entity} {relation} {value}"` string is sent to the cloud embedding API | Opt-in only; default is offline nomic-embed-text-v1.5 | Operators must understand data flows before enabling cloud embed |
| T8-D1 | Provider rate limits block recall | Denial of service | Cloud embedding rate limit causes recall failures | Per-provider retry with backoff; local fallback if configured | No automatic local fallback in v1.1-draft |

---

## 7. Risk Register

Each risk is rated on:
- **Likelihood**: High / Medium / Low (given the current deployment baseline, not worst-case)
- **Impact**: Critical / High / Medium / Low
- **Priority**: product of the two

| ID | Threat refs | Finding | Likelihood | Impact | Priority | Spec ref | Phase 12? | Status |
|---|---|---|---|---|---|---|---|---|
| R-01 | T2-S1 | No mTLS: federation peer impersonation possible without client cert verification | Medium | High | High | §22.1 | Yes | Open |
| R-02 | T1-D1, T1-D2, T3-D1 | No per-principal rate limits on writes and recalls | High | Medium | High | §22.4 | Yes | Open |
| R-03 | T1-S1, T7-S1 | No enforced API key max-age; keys do not expire | Medium | High | High | §22.2 | Yes | Open |
| R-04 | T4-I1 | At-rest encryption (SQLCipher) opt-in; default deployment stores facts in plaintext | Medium | High | High | §3 | Partial | Open |
| R-05 | T3-S1 | Prompt injection via adversarial facts recalled into agent context | High | High | Critical | §19.7 | Mitigated (sanitizer) | Residual |
| R-06 | T2-T1 | Federation replay protection fuzz test coverage incomplete | Low | High | Medium | §22.5 | Yes | Open |
| R-07 | T6-S1 | Obsidian plugin API key stored in plaintext settings | Low | Medium | Low | — | No | Accepted |
| R-08 | T4-T2, T4-I2 | libSQL cloud backend: facts in transit to Turso without additional app-layer encryption | Medium | Medium | Medium | §3.2 | No | Accepted (operator TLS) |
| R-09 | T1-R1, T7-R1 | No general-purpose audit log for sensitive scope reads or admin actions | High | Medium | High | §22.3 | Yes | Open |
| R-10 | T5-R1 | Org manifest rotation events not consistently submitted to transparency log | Low | Medium | Low | §19.2.6, §22.7 | Yes | Open |
| R-11 | — | Container not distroless; Linux capabilities not fully dropped | Low | Low | Low | §22.6 | Yes | Open |
| R-12 | T3-D1, T3-E1 | Agent tool surface: no per-agent budget or rate limit without §22.4 | High | Medium | High | §22.4, §21 | Yes | Open |
| R-13 | T8-I1 | Cloud embedding opt-in: fact content sent to external provider when enabled | Low | Medium | Low | §20.2 | No | Accepted (opt-in) |
| R-14 | T2-E1 | Capability token scope/verb not fully validated at federation admission in v1.0-rc | Low | High | Medium | §19.3.3 | Amended in §22 | Open |

### Risk register key

- **Open** — not yet mitigated; awaiting Phase 12 delivery or design decision.
- **Residual** — partially mitigated; residual risk documented.
- **Accepted** — risk acknowledged; no planned mitigation for the stated reason.

---

## 8. Mitigations Summary (Phase 12 Targets)

| Risk | Mitigation | Spec section |
|---|---|---|
| R-01 | mTLS on all federation ports; TLS 1.3 floor; SAN/entity_uri binding | §22.1 |
| R-02 | Per-principal token-bucket quotas on 7 dimensions | §22.4 |
| R-03 | Enforced key max-age; expiring-soon surface; rotation runbook | §22.2 |
| R-05 | Recall-time content sanitizer (shipped); fuzz-tested (Phase 12) | §19.7, §22.5 |
| R-06 | Fuzz tests on federation replay protection; nonce cache survival test | §22.5 |
| R-09 | 13-event-type audit log with WAL ordering and 90-day retention | §22.3 |
| R-10 | `key_rotation` log entry mandatory on every rotation; logged before activation | §22.2.3 |
| R-11 | Distroless base image; non-root UID 1000; read-only fs; seccomp | §22.6 |
| R-12 | Same as R-02; per-agent quota dimension in §22.4 | §22.4 |
| R-14 | Normative verb/object validation at capability token admission (§22 amendments) | §19.3.3 |

---

## 9. Residual Risk After Phase 12

After Phase 12 hardening is complete:

1. **Prompt injection (R-05)** remains the most difficult residual risk. The sanitizer (§19.7) provides defense-in-depth but cannot exhaustively block novel injection patterns. Mitigations: sandboxed agent execution at the agent-runtime layer; token budget controls that limit context window exposure.

2. **At-rest encryption (R-04)** is operator-configurable but not default-on. Operators handling regulated data must explicitly enable SQLCipher. This is a deliberate tradeoff for deployment simplicity.

3. **Obsidian plugin key storage (R-07)** depends on the OS keychain or Obsidian's own plugin isolation, which Stigmem does not control. Mitigation: rotate keys promptly if another plugin is suspected of access.

4. **Cloud embedding data residency (R-13)** is an accepted risk for operators who opt into cloud embedding. Fact payloads are sent to the embedding provider. Operators must review their data classification before enabling.

5. **HLC cursor manipulation (T2-T2)** has no current normative bound. Operators who run federated deployments should monitor for anomalous HLC drift.

---

## 10. Review and Maintenance

- This threat model is reviewed on every spec revision that introduces a new trust boundary or modifies an existing one.
- Phase 12 closed items will be updated to **Mitigated** in the risk register upon hardening spec delivery and regression test confirmation.
- Community pen-test findings that fall outside this model's scope should be submitted via the [Community Pen-Test Handbook](../../docs/docs/security/pen-test.md).
