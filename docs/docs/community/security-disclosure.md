---
id: security-disclosure
title: Security & Responsible Disclosure
sidebar_label: Security Disclosure
description: Vulnerability reporting, responsible disclosure policy, pen-testing scope, safe-harbor terms, and security posture for the Stigmem project.
---

# Security & Responsible Disclosure

*Audience: security researchers, pen testers, node operators, protocol implementers.*

---

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private advisory path:

1. Go to the [Security Advisories](https://github.com/eidetic-labs/stigmem/security/advisories) page.
2. Click **"Report a vulnerability"**.
3. Include: description, reproduction steps, environment (backend type, Stigmem version, config), potential impact, and suggested fix if known.

**Response SLAs:**

- Acknowledgement within **48 hours**.
- Status update within **7 days**.
- Patch target: **14 days** for Critical/High findings.
- Coordinated disclosure window: **90 days** from acknowledgment (shorter for actively exploited issues).

See [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) for the full disclosure policy.

For the formal threat model (trust boundaries, STRIDE analysis, risk register), see [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

---

## Supported versions

| Version | Supported |
| ------- | --------- |
| `0.9.0a*` (the v0.9.0aN alpha series alpha — current) | Yes — pre-release; no stability guarantee. |
| `1.0.0rc1` (retracted) | No — yanked from PyPI; see the retraction post linked from `README.md`. |
| `< 0.9.0a1` (development checkpoints `pre-reset`–`v2.0`) | No — internal checkpoints, not tagged releases. |

The canonical `SECURITY.md` at the repo root is the source of truth for supported versions; this page mirrors it.

---

## Pen-testing scope

### In scope

| Surface | Notes |
|---|---|
| **Reference node HTTP API** — `/v1/facts`, `/v1/query`, `/v1/lint`, `/v1/synthesis`, `/v1/decay`, `/v1/conflicts`, `/v1/federation/*` | All endpoints, authenticated and unauthenticated paths |
| **Federation handshake and replication** | PeerDeclaration signing, HLC cursor handling, replay protection |
| **Authentication** | API-key issuance, storage (Argon2id hashing), validation, scope enforcement |
| **Source Attestation (spec §18)** | Enforcement modes (`enforce`, `warn`, `off`); entity-URI binding |
| **Memory Garden ACLs (spec §17)** | Role escalation paths; garden boundary enforcement |
| **MCP adapter** | `assert_fact` and `query_facts` tool surface |
| **OpenClaw / Claude Code adapter** | Memory read/write paths |

### Out of scope

| Surface | Reason |
|---|---|
| Docs build toolchain (Docusaurus, npm transitive deps) | Build-time only; no user-controlled input path |
| Third-party dependencies (libSQL cloud, Turso, Postgres, Rekor) | Report findings to the upstream project |
| Rate limiting / resource exhaustion with no clear exploit path | Known gap; tracked as a planned hardening item |
| Social engineering or phishing | Out of scope for all security programs |
| `https://docs.stigmem.dev` (static docs site) | No user data; no dynamic server-side logic |

For the full structured engagement guide — including the report template, reproducer expectations, and recognition model — see the [Community Pen-Test Handbook](../security/pen-test.md).

---

## Safe-harbor terms

If you conduct good-faith testing within the scope above, Eidetic Labs will not pursue legal action and will publicly credit you in `SECURITY.md` and the relevant release notes (unless you prefer anonymity).

**"Good faith" means:**
- You do not access, exfiltrate, or modify data that is not yours.
- You test against your own node instance or a dedicated test environment.
- You report findings privately before public disclosure.
- You do not cause service disruption to other users' nodes.
- You do not exploit a finding beyond what is necessary to confirm it exists.

---

## Severity guidance

Use CVSS v3.1 as the primary severity signal. For Stigmem-specific surfaces:

| Severity | Examples |
|---|---|
| **Critical** | Authentication bypass; remote code execution; federation peer impersonation; reading `local` or `team` facts without authorization |
| **High** | Privilege escalation; scope boundary bypass; replay-attack success; Source Attestation bypass in `enforce` mode |
| **Medium** | DoS with a clear exploit path; SSRF via federation pull path; information disclosure beyond error messages |
| **Low** | Minor information disclosure (e.g., internal stack traces); non-critical config defaults that weaken posture |
| **Informational** | Defense-in-depth suggestions; hardening recommendations without a clear exploit |

---

## Security posture — v0.9.0a1

> **Posture-reset note.** The 2026-05-08 reset to `v0.9.0a1` carried forward the dependency-fix posture from the withdrawn v1.0 release-candidate snapshot — the same patched package versions are still in effect. Several **threat-model** controls (mTLS-default federation, persistent audit log, per-principal rate limits, capability-level cross-org instruction validation, bounded HLC skew, the ADR-016 storage-immutability stack) are scheduled for the v0.9.0bN beta series and are **not yet in effect** at v0.9.0a1. Adopters running federation across organizational boundaries should wait for the v0.9.0bN beta series per `LIMITATIONS.md` at the repo root: [github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md](https://github.com/Eidetic-Labs/stigmem/blob/main/LIMITATIONS.md). The canonical security posture lives in repo-root `SECURITY.md`; this page mirrors the dependency-alert summary.

The dependency-alert posture carried forward to v0.9.0a1 has **zero unaddressed Dependabot alerts**:

| Category | Count |
| -------- | ----- |
| Dependabot alerts resolved by the dep upgrade sweep | 20 |
| Docs build toolchain alerts (non-exploitable, suppressed) | 7 |
| Unaddressed / escalated blockers | 0 |

### Security controls in effect

| Control | Detail |
| ------- | ------ |
| **Authentication** | API keys enforced on all write endpoints; per-scope restrictions (spec §3.5) |
| **Federation** | Ed25519 peer handshake; HLC timestamps prevent replay attacks (spec §6) |
| **Input validation** | Pydantic on all HTTP endpoints; malformed payloads return 422 before business logic |
| **Secrets** | No credentials in the repository; Docker Compose uses environment variable injection |
| **CI gate** | `pip-audit`, `pnpm audit`, and `bandit` run as blocking steps on every PR |

---

## Audit tooling

Three tools run as blocking CI steps (`.github/workflows/ci.yml`) on every push and pull request.

| Tool | Scope | Gate |
| ---- | ----- | ---- |
| `pip-audit` | Python dependencies (`uv.lock`) | `python-tests` job; exits non-zero on any moderate+ CVE |
| `pnpm audit` | Node.js dependencies (`pnpm-lock.yaml`) | `node-tests` job; `--audit-level=moderate` |
| `bandit` | Python source (`node/src/`, `sdks/stigmem-py/src/`) | `python-tests` job; configured in `[tool.bandit]` in `pyproject.toml` |

**Run locally:**

```bash
# Python dependency audit
uv run pip-audit

# Python static security analysis
uv run bandit -r node/src/ sdks/stigmem-py/src/ -c pyproject.toml

# Node.js dependency audit
pnpm audit --audit-level=moderate
```

---

## Running a test environment

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

For federation testing, the `docker-compose.federation.yml` spins up a 2-node topology:

```bash
docker compose -f docker-compose.federation.yml up -d
```

A 4-node test topology is documented in [Federation: 4-Node Soak](../concepts/federation/federation-4node.md).

---

## Coordinated disclosure

The default window is **90 days** from acknowledgment of a valid finding. Exceptions:

- **Actively exploited in the wild** — faster coordination with reporter agreement.
- **Straightforward fix available** — faster publication timeline communicated.
- **90 days is not enough** — extension discussed with the reporter.

---

## Bug bounty

Stigmem does not currently operate a paid bug bounty program. Valid findings are recognized with:
- Public credit in `SECURITY.md` and the fixing release's changelog.
- Attribution in the spec errata if the finding affects wire-format or protocol behavior.

---

## See also

- [Community Pen-Test Handbook](../security/pen-test.md) — full engagement guide with report template
- [Container Hardening](../security/container-hardening.md) — distroless, seccomp, non-root
- [Key Rotation](../security/key-rotation.md) — Ed25519 key lifecycle and dual-trust windows
- [Audit & Quotas](../security/audit-and-quotas.md) — audit log surface and per-principal rate limiting
