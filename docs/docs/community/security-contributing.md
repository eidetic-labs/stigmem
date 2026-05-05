---
title: Security & Pen Testing
sidebar_label: Security & Pen Testing
description: How to contribute security research and pen testing to the Stigmem project — scope, safe-harbor terms, severity guidance, and how to engage.
---

# Security & Pen Testing

*Audience: security researchers, pen testers, protocol implementers.*

---

The Stigmem project welcomes security research and pen testing as a community contribution. Stigmem is an open protocol with a federated trust model — external scrutiny makes it stronger. This page provides an overview of the scope, safe-harbor terms, severity guidance, and engagement process for community security work.

For the full structured engagement guide — including the report template, reproducer expectations, severity guidance, and recognition model — see the [Community Pen-Test Handbook](../security/pen-test.md).

For the formal threat model (trust boundaries, STRIDE analysis, risk register), see [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

For the responsible-disclosure policy and supported-version matrix, see [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md).

---

## Scope

### In scope

| Surface | Notes |
|---|---|
| **Reference node HTTP API** — `/v1/facts`, `/v1/query`, `/v1/lint`, `/v1/synthesis`, `/v1/decay`, `/v1/conflicts`, `/v1/federation/*` | All endpoints, authenticated and unauthenticated paths |
| **Federation handshake and replication** | PeerDeclaration signing, HLC cursor handling, replay protection |
| **Authentication** | API-key issuance, storage (Argon2id hashing), validation, scope enforcement at read and write time |
| **Source Attestation (spec §18)** | Enforcement modes (`enforce`, `warn`, `off`); entity-URI binding |
| **Memory Garden ACLs (spec §17)** | Role escalation paths; garden boundary enforcement |
| **MCP adapter** | `assert_fact` and `query_facts` tool surface |
| **OpenClaw / Claude Code adapter** | Memory read/write paths |

### Out of scope

| Surface | Reason |
|---|---|
| Docs build toolchain (Docusaurus, npm transitive deps) | Build-time only; no user-controlled input path in the deployed docs site |
| Third-party dependencies (libSQL cloud, Turso, Postgres, Rekor) | Report findings to the upstream project |
| Rate limiting / resource exhaustion with no clear exploit path | Known gap; tracked as a planned Phase 12 hardening item |
| Social engineering or phishing | Out of scope for all security programs |
| `https://docs.stigmem.dev` (static docs site) | No user data; no dynamic server-side logic |

---

## Safe-harbor terms

If you conduct good-faith testing within the scope above, Eidetic Labs will not pursue legal action and will publicly credit you in `SECURITY.md` and the relevant release notes (unless you prefer anonymity).

**"Good faith" means:**
- You do not access, exfiltrate, or modify data that is not yours.
- You test against your own node instance or a dedicated test environment — not a third-party node without permission from that operator.
- You report findings privately before public disclosure (see [Coordinated Disclosure](#coordinated-disclosure)).
- You do not cause service disruption to other users' nodes.
- You do not exploit a finding beyond what is necessary to confirm it exists.

---

## Severity guidance

Use CVSS v3.1 as the primary severity signal. For Stigmem-specific surfaces:

| Severity | Examples |
|---|---|
| **Critical** | Authentication bypass; remote code execution; federation peer impersonation; reading `local` or `team` facts without authorization |
| **High** | Privilege escalation within the API; scope boundary bypass (e.g., reading `local` facts via a `public` query path); replay-attack success against the federation handshake; Source Attestation bypass in `enforce` mode |
| **Medium** | Denial-of-service with a clear exploit path (e.g., memory exhaustion via crafted federation payload); SSRF via the federation replication pull path; information disclosure beyond minor error messages |
| **Low** | Minor information disclosure (e.g., internal stack traces in error responses); non-critical config defaults that weaken security posture |
| **Informational** | Defense-in-depth suggestions; hardening recommendations without a clear exploit path; deviations from best practice with no immediate impact |

---

## How to engage

### Reporting a finding

Use GitHub's private advisory path — **do not open a public issue for security findings**:

1. Go to [Security Advisories](https://github.com/eidetic-labs/stigmem/security/advisories).
2. Click **"Report a vulnerability"**.
3. Include:
   - Description and reproduction steps
   - Environment: backend type, Stigmem version, relevant config
   - Impact assessment (what an attacker could do)
   - Suggested fix if you have one

**Response SLAs:**
- Acknowledgement within **48 hours**.
- Status update within **7 days** (patch target or scope clarification).
- Patch target: **14 days** for Critical/High findings.
- Coordinated disclosure window: **90 days** from acknowledgment (shorter for actively exploited issues; see below).

### Coordinating a pen test

If you want to run a structured engagement (vs. individual finding reports), open a [GitHub Discussion](https://github.com/eidetic-labs/stigmem/discussions) in the Stigmem repo with:

- Your intended scope (which surfaces, which spec version).
- Your test environment setup (your own node, isolated network, etc.).
- Your proposed timeline.

The team will confirm the scope, share any active-hardening context that's relevant (e.g., "we know X is weak, Phase 12 addresses it"), and coordinate credit.

---

## Coordinated disclosure

The default window is **90 days** from acknowledgment of a valid finding. Exceptions:

- **Actively exploited in the wild** — we coordinate faster and may disclose sooner with your agreement.
- **Straightforward fix available** — we target faster publication and will communicate the timeline.
- **90 days is not enough** — if a patch will take longer, we will discuss an extension with the reporter.

We keep reporters informed of patch progress and release dates throughout the window.

---

## Running a test environment

The fastest way to get a disposable Stigmem node for testing:

```bash
# Clone the repo
git clone https://github.com/eidetic-labs/stigmem
cd stigmem

# Start a node with Docker Compose
docker compose up -d stigmem-node

# Create a test API key
curl -X POST http://localhost:8000/v1/admin/keys \
  -H "Authorization: Bearer $STIGMEM_ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{"label": "pentest", "scopes": ["public", "team"]}'
```

For federation testing, the `docker-compose.federation.yml` in the repo spins up a 2-node topology:

```bash
docker compose -f docker-compose.federation.yml up -d
```

A 4-node test topology (including backpressure and scope propagation invariants) is documented in [Federation: 4-Node Soak](../guides/federation-4node.md).

---

## Known hardening gaps (Phase 12 backlog)

The following are known gaps planned for Phase 12. You are welcome to test and report them — findings in this list will be triaged as known rather than novel, but novel attack paths against them (beyond the listed gap) are still valuable findings:

| Gap | Phase 12 target |
|---|---|
| mTLS for federation peer connections (currently TLS only, no cert pinning) | mTLS + cert-pinning option |
| API-key rotation: no enforced max-age | Enforced max-age + expiring-soon surface |
| Per-principal write/recall rate limits | Quota + rate-limit enforcement |
| Container runs as non-root but not distroless | Distroless base, read-only fs, dropped capabilities |
| Federation replay-protection fuzz test coverage | Fuzz tests + HLC + nonce end-to-end verification |
| Constant-time crypto: audit pending | Full constant-time audit of Ed25519 path |

---

## Bug bounty

Stigmem does not currently operate a paid bug bounty program. Valid findings are recognized with:
- Public credit in `SECURITY.md` and the fixing release's changelog.
- Attribution in the spec errata if the finding affects wire-format or protocol behavior.

This may change as the project scales.
