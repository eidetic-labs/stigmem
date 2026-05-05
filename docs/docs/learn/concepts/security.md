---
id: security
title: Security
sidebar_label: Security
description: Security policy, responsible disclosure, v1.0-rc posture, and audit tooling for the Stigmem reference node.
---

# Security

*Audience: node operators, security researchers, protocol implementers.*

---

## Reporting a vulnerability

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private advisory path:

1. Go to the [Security Advisories](https://github.com/eidetic-labs/stigmem/security/advisories) page.
2. Click **"Report a vulnerability"**.
3. Fill in the details: description, reproduction steps, potential impact, and suggested fix if known.

We will acknowledge your report within **48 hours** and aim to release a patch within **14 days** for critical vulnerabilities. We follow coordinated disclosure and ask reporters to allow 90 days before public disclosure.

See [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) for the full disclosure policy.

---

## Supported versions

| Version | Supported |
| ------- | --------- |
| 1.0-rc  | Yes       |
| 0.x     | Yes (until v1.0 stable) |
| < 0.9   | No        |

---

## Security posture — v1.0-rc

As of 2026-05-03, the v1.0-rc release has **zero unaddressed security concerns**:

| Category | Count |
| -------- | ----- |
| Dependabot alerts resolved by the v1.0-rc dep upgrade sweep | 20 |
| Docs build toolchain alerts (non-exploitable, suppressed) | 7 |
| Unaddressed / escalated blockers | 0 |

The full triage — including per-CVE tables for Next.js, vite, esbuild, and docs toolchain findings — is in [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md).

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

:::info Docs build toolchain
The `pnpm audit` output includes findings from `docusaurus-plugin-openapi-docs` transitive dependencies. These are build-time only with no user-controlled input pathway — see the full suppression rationale in `SECURITY.md`.
:::
