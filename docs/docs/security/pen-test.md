---
title: Community Pen-Test Handbook
sidebar_label: Pen-Test Handbook
description: Everything a security researcher or pen tester needs to run a structured engagement against Stigmem — scope, safe harbor, reproducer expectations, report template, and recognition.
audience: Operator
---

# Community Pen-Test Handbook

*Audience: security researchers, penetration testers, protocol security reviewers.*

---

Stigmem is an open federated protocol. External security scrutiny makes it stronger. This handbook covers everything you need to run a structured engagement — from scoping your test to getting your findings in front of the maintainers.

For the project's vulnerability disclosure policy and supported-version matrix, see [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md).

For the technical threat model (trust boundaries, STRIDE analysis, risk register), see [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

---

## 1. In-Scope Targets

The following surfaces are explicitly in scope for community pen testing:

| Surface | Notes |
|---|---|
| **Reference node HTTP API** — `/v1/facts`, `/v1/query`, `/v1/recall`, `/v1/cards/*`, `/v1/graph/*`, `/v1/synthesis`, `/v1/decay`, `/v1/conflicts`, `/v1/subscriptions`, `/v1/federation/*`, `/v1/admin/*` | All endpoints, authenticated and unauthenticated paths. Both read and write surfaces. |
| **Federation handshake and replication** | PeerDeclaration signing, HLC cursor handling, replay protection, capability token validation |
| **Authentication and API key lifecycle** | Key issuance, storage (Argon2id hashing), validation, scope enforcement, revocation |
| **Capability token issuance and validation** | Ed25519 signing, expiry, nonce, verb/object scope enforcement (spec §19.3) |
| **Source Attestation (spec §18)** | Enforcement modes (`enforce`, `warn`, `off`); entity-URI binding |
| **Memory Garden ACLs (spec §17)** | Role escalation paths; garden boundary enforcement; quarantine admit/release |
| **MCP adapter** | `assert_fact`, `query_facts`, `recall`, `lint_scope` tool surface |
| **OpenClaw / Claude Code adapter** | Memory read/write paths |
| **Recall pipeline** | Scope isolation across lexical, vector, and graph stages (spec §20.3) |
| **Audit log endpoints** (Phase 12) | Access control on `/v1/admin/audit-log`; log tamper-resistance |
| **Per-principal quota enforcement** (Phase 12) | Correct application of token-bucket ceilings; bypass attempts |

### Priority finding categories

The following finding classes are of the highest interest to maintainers:

- **Authentication bypass** — accessing write endpoints without a valid API key, or escalating a `public`-scoped key to read/write `team` or `local` facts.
- **Cross-org data leakage** — a capability token or API key granting access to facts beyond its declared scope.
- **Federation peer impersonation** — successfully acting as a peer node without a valid mTLS certificate and matching org manifest.
- **Capability token replay or forgery** — replaying a revoked token, forging a signature, or bypassing the nonce/timestamp window.
- **Prompt injection via the recall pipeline** — bypassing the recall-time content sanitizer (spec §19.7) to inject instructions into an LLM context via stored fact values.
- **Quarantine garden bypass** — causing an untrusted fact to enter the main fact store without passing through quarantine review.
- **Source Attestation bypass** — writing facts without a valid attestation in `enforce` mode.

---

## 2. Out-of-Scope Targets

The following are explicitly **not in scope**. Testing these will not result in credit and may violate third-party terms of service:

| Surface | Reason |
|---|---|
| **`https://docs.stigmem.dev`** (static documentation site) | No user data; no dynamic server-side logic |
| **Docs build toolchain** (Docusaurus, npm transitive deps) | Build-time only; no user-controlled input path in the deployed docs site |
| **Third-party dependencies** (libSQL cloud, Turso, PostgreSQL, Rekor/Sigstore) | Report findings to the upstream project directly |
| **Third-party nodes not operated by you** | You must only test against nodes you operate or have explicit permission to test |
| **Rate limiting / resource exhaustion with no exploit path** | Tracked as a known gap; use `fact_write` quota dimension (Phase 12) to test post-hardening |
| **Social engineering or phishing** | Out of scope for all security programs |
| **Physical access to infrastructure** | Not applicable to community testers |

---

## 3. Safe-Harbor Terms

If you conduct good-faith testing **within the scope above**, Eidetic Labs will not pursue legal action and will publicly credit you in `SECURITY.md` and the relevant release notes (unless you prefer anonymity).

**"Good faith" means:**

1. You do not access, exfiltrate, or modify data that is not yours.
2. You test against **your own node instance** or a dedicated test environment — not a third-party node without explicit written permission from that operator.
3. You report findings **privately** before public disclosure (see [§8 Disclosure Timeline](#8-disclosure-timeline)).
4. You do not cause service disruption to other operators or their users.
5. You do not exploit a finding beyond what is necessary to confirm it exists.
6. You do not automate requests at a rate that would degrade a shared test environment.

Violating any of the above conditions voids the safe-harbor commitment for that engagement.

---

## 4. Setting Up a Test Environment

The fastest way to get a disposable Stigmem node for testing:

```bash
# Clone the repo
git clone https://github.com/eidetic-labs/stigmem
cd stigmem

# Start a node with Docker Compose (SQLite backend, no federation)
docker compose up -d stigmem-node

# Create a test API key (save the returned plaintext key — it is shown once only)
curl -X POST http://localhost:8000/v1/admin/keys \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"label": "pentest", "scopes": ["public", "team"]}'
```

For **federation testing**, a 2-node topology is available:

```bash
docker compose -f docker-compose.federation.yml up -d
```

For a **4-node federation soak** including backpressure and scope-propagation invariants, see the [Federation: 4-Node Soak guide](../concepts/federation/federation-4node.md).

### Recommended test matrix

| Test area | Recommended setup |
|---|---|
| API auth / scope | Single node, multiple keys with different scopes |
| Federation peer auth | 2-node Docker Compose topology |
| Capability token replay | Single node, issue + replay with modified nonce/timestamp |
| Recall pipeline scope isolation | Single node, facts asserted in mixed scopes, queries from lower-privilege key |
| Prompt injection via recall | Single node, adversarial fact values, recall via MCP adapter |
| Quarantine bypass | 2-node topology, assert from low-trust peer, inspect quarantine |

---

## 5. Reproducer Expectations

Every finding submitted via GitHub private advisory should include a **self-contained reproducer**. Findings without a working reproducer will be triaged as "needs more info" and may not receive credit until one is provided.

A complete reproducer includes:

1. **Environment** — Stigmem version/commit, backend type (SQLite/libSQL/Postgres), OS.
2. **Setup steps** — exact commands to provision a test node and any required keys or data.
3. **Attack steps** — the exact request sequence, including all HTTP headers and bodies, in order.
4. **Expected behavior** — what should happen if the control is working correctly.
5. **Observed behavior** — what actually happened (HTTP response, data returned, side effect).
6. **Impact assessment** — what an attacker gains; whose data; what privilege level; can it pivot.

**Example reproducer for a hypothetical scope bypass:**

```
Environment: stigmem v0.9.0a1, SQLite backend, Docker Compose
Commit: abc1234

Setup:
  docker compose up -d stigmem-node
  ADMIN_KEY=$(docker compose exec stigmem-node cat /run/secrets/admin_key)
  curl -X POST http://localhost:8000/v1/admin/keys \
    -H "Authorization: Bearer $ADMIN_KEY" \
    -d '{"label":"victim", "scopes":["team"]}'   # returns: VICTIM_KEY=stgm_...
  curl -X POST http://localhost:8000/v1/admin/keys \
    -H "Authorization: Bearer $ADMIN_KEY" \
    -d '{"label":"attacker", "scopes":["public"]}' # returns: ATTACKER_KEY=stgm_...
  curl -X POST http://localhost:8000/v1/facts \
    -H "Authorization: Bearer $VICTIM_KEY" \
    -d '{"entity":"stigmem://victim/secret","relation":"value","value":"secret123","scope":"team"}'

Attack:
  curl -X POST http://localhost:8000/v1/recall \
    -H "Authorization: Bearer $ATTACKER_KEY" \
    -d '{"query":"secret","scopes":["public","team"]}'

Expected: Only public-scoped facts returned; team-scoped facts excluded.
Observed: team-scoped fact "secret123" returned in response.

Impact: Any public-scoped API key can read all team-scoped facts. Full data exfiltration of team scope.
```

---

## 6. Report Template

Use this template when opening a GitHub Security Advisory:

```
## Summary
[One-sentence description of the vulnerability class and impact.]

## Vulnerability class
[OWASP / STRIDE category, e.g., "Broken Object-Level Authorization (BOLA)", "Authentication bypass"]

## CVSS v3.1 score and vector
Score: X.X
Vector: CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N

## Affected versions
[e.g., v1.0-rc, all versions up to commit abc1234]

## Environment
- Stigmem version/commit:
- Backend type:
- OS:

## Reproducer
[Self-contained steps per §5 above]

## Expected behavior

## Observed behavior

## Impact
[What can an attacker do? Whose data is at risk? What privilege level is achieved?]

## Suggested fix (optional)
[Concrete code-level or protocol-level fix if you have one]

## Disclosure preference
[ ] Credit me publicly as: [name/handle]
[ ] I prefer anonymous credit
[ ] I do not need credit
```

---

## 7. Severity Guidance

Use CVSS v3.1 as the primary severity signal. For Stigmem-specific surfaces:

| Severity | Examples |
|---|---|
| **Critical** | Authentication bypass; remote code execution; federation peer impersonation; reading `local` or `team` facts without authorization; capability token forgery |
| **High** | Privilege escalation within the API; scope boundary bypass (reading `local` facts via a `public` query path); replay-attack success against the federation handshake; Source Attestation bypass in `enforce` mode |
| **Medium** | Denial-of-service with a clear exploit path (e.g., memory exhaustion via crafted federation payload); SSRF via the federation replication pull path; information disclosure beyond minor error messages; quarantine garden bypass |
| **Low** | Minor information disclosure (e.g., internal stack traces in error responses); non-critical config defaults that weaken security posture |
| **Informational** | Defense-in-depth suggestions; hardening recommendations without a clear exploit path; deviations from best practice with no immediate impact |

---

## 8. Disclosure Timeline

The Stigmem project follows **coordinated disclosure** with a default window of **90 days** from acknowledgment of a valid finding.

| Event | Target SLA |
|---|---|
| Initial acknowledgment | 48 hours from receipt |
| Scope / validity confirmation | 7 days from receipt |
| Patch target (Critical / High) | 14 days from confirmation |
| Patch target (Medium) | 45 days from confirmation |
| Patch target (Low / Informational) | Next scheduled release |
| Coordinated public disclosure | 90 days from acknowledgment (default) |

**Exceptions to the 90-day window:**

- **Actively exploited in the wild** — we coordinate with you and may disclose sooner, potentially within 7 days.
- **Straightforward fix available** — we target faster publication and will communicate the updated timeline.
- **90 days is insufficient** — if a patch requires architectural changes that take longer, we will discuss an extension with you. We will not request an extension more than once without a concrete timeline.

We keep reporters informed of patch progress and release dates throughout the window. If you have not heard from us within 7 days of filing, ping the advisory thread directly.

---

## 9. Coordinating a Structured Engagement

If you want to run a structured pen test (vs. individual ad-hoc finding reports), open a [GitHub Discussion](https://github.com/eidetic-labs/stigmem/discussions) with:

- Your intended scope (which API surfaces, which spec version, which trust boundary).
- Your test environment setup (your own node, isolated network, etc.).
- Your proposed timeline.
- Any active-hardening context you'd like to know about (e.g., "we're hardening TB-2 in Phase 12 — here's what's already in flight").

Maintainers will confirm scope, share any active-hardening context, and coordinate acknowledgment and credit at the end of your engagement.

---

## 10. Known Hardening Gaps

The following are **known gaps** planned for Phase 12 hardening. You are welcome to test and report them — findings in this list will be triaged as **known** rather than novel, but **novel attack paths** against them (beyond the listed gap) are still valuable findings and eligible for full credit:

| Gap | Phase 12 target |
|---|---|
| mTLS for federation peer connections (currently TLS only, no client cert) | mTLS + TLS 1.3 floor + SAN/entity_uri binding (spec §22.1) |
| API-key rotation: no enforced max-age | Enforced max-age + expiring-soon surface (spec §22.2) |
| Per-principal write/recall rate limits: not enforced | Token-bucket quotas on 7 dimensions (spec §22.4) |
| Audit log: not yet shipped | 13-event-type audit log, WAL ordering, 90-day retention (spec §22.3) |
| Container runs as non-root but not distroless | Distroless base, read-only fs, dropped capabilities (spec §22.6) |
| Federation replay-protection fuzz test coverage | Fuzz tests + HLC + nonce end-to-end verification (spec §22.5) |
| Constant-time crypto: audit pending | Full constant-time audit of Ed25519 path |

The full threat model with STRIDE analysis per trust boundary, including status of all known risks, is at [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

---

## 11. Recognition

Stigmem does not currently operate a paid bug bounty program. Valid findings are recognized with:

- **Hall of fame** — your name or handle is added to the `SECURITY.md` acknowledgments section and the fixing release's changelog.
- **Attribution in the spec errata** — if your finding affects wire-format or protocol behavior (spec §§1–22), you are credited in the spec changelog as a contributor to that revision.
- **Coordinated disclosure credit** — the GitHub Security Advisory, when published, lists you as the reporter.

If you prefer to remain anonymous, say so in your report template (`[ ] I prefer anonymous credit`) and we will honor that throughout all public communications.

This recognition model may evolve as the project scales.
