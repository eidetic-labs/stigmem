---
id: security-disclosure
title: Security & Responsible Disclosure
sidebar_label: Security Disclosure
description: Vulnerability reporting, responsible disclosure policy, pen-testing scope, safe-harbor terms, and security posture for the Stigmem project.
---

# Security & Responsible Disclosure

<p className="stigmem-meta"><span>5 min read</span><span>Security researcher · Pen tester</span><span>v0.9.0a2</span></p>

<div className="stigmem-lead">

**What this page covers**

Vulnerability reporting, responsible disclosure policy, pen-testing
scope, safe-harbor terms, and security posture for the Stigmem
project.

</div>

**Audience:** security researchers, pen testers, node operators, protocol implementers.

## Reporting a vulnerability

<div className="stigmem-keypoint">

**Do not open a public GitHub issue for security vulnerabilities.**

Use GitHub's private advisory path.

</div>

<ol className="stigmem-steps">
<li>Go to the <a href="https://github.com/eidetic-labs/stigmem/security/advisories">Security Advisories</a> page.</li>
<li>Click <strong>"Report a vulnerability"</strong>.</li>
<li>Include: description, reproduction steps, environment (backend type, Stigmem version, config), potential impact, and suggested fix if known.</li>
</ol>

**Response SLAs:**

<div className="stigmem-fields">

<div>
<dt>Milestone</dt>
<dt><span className="stigmem-fields__type">Target</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Acknowledgement</dt>
<dt><span className="stigmem-fields__type">48 hours</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Status update</dt>
<dt><span className="stigmem-fields__type">7 days</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Patch target</dt>
<dt><span className="stigmem-fields__type">14 days</span></dt>
<dd>For Critical/High findings.</dd>
</div>

<div>
<dt>Coordinated disclosure</dt>
<dt><span className="stigmem-fields__type">90 days</span></dt>
<dd>From acknowledgment. Shorter for actively exploited issues.</dd>
</div>

</div>

See [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md) for the full disclosure policy.

## Supported versions

<div className="stigmem-fields">

<div>
<dt>Version</dt>
<dt><span className="stigmem-fields__type">Supported</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>0.9.0a&#42;</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>The v0.9.0aN alpha series — current. Pre-release; no stability guarantee.</dd>
</div>

<div>
<dt><code>retracted pre-reset label</code></dt>
<dt><span className="stigmem-fields__type">no (retracted)</span></dt>
<dd>Retracted label; no PyPI artifact was published.</dd>
</div>

<div>
<dt><code>&lt; 0.9.0a1</code></dt>
<dt><span className="stigmem-fields__type">no</span></dt>
<dd>Internal checkpoints (<code>pre-reset</code>–<code>v2.0</code>), not tagged releases.</dd>
</div>

</div>

## Pen-testing scope

### In scope

<div className="stigmem-fields">

<div>
<dt>Surface</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Reference node HTTP API</dt>
<dt><span className="stigmem-fields__type">all routes</span></dt>
<dd><code>/v1/facts</code>, <code>/v1/query</code>, <code>/v1/lint</code>, <code>/v1/synthesis</code>, <code>/v1/decay</code>, <code>/v1/conflicts</code>, <code>/v1/federation/&#42;</code>. Authenticated and unauthenticated paths.</dd>
</div>

<div>
<dt>Federation handshake</dt>
<dt><span className="stigmem-fields__type">protocol</span></dt>
<dd>PeerDeclaration signing, HLC cursor handling, replay protection.</dd>
</div>

<div>
<dt>Authentication</dt>
<dt><span className="stigmem-fields__type">credential</span></dt>
<dd>API-key issuance, storage (Argon2id hashing), validation, scope enforcement.</dd>
</div>

<div>
<dt>Source Attestation</dt>
<dt><span className="stigmem-fields__type">spec §18</span></dt>
<dd>Enforcement modes (<code>enforce</code>, <code>warn</code>, <code>off</code>); entity-URI binding.</dd>
</div>

<div>
<dt>Memory Garden ACLs</dt>
<dt><span className="stigmem-fields__type">spec §17</span></dt>
<dd>Role escalation paths; garden boundary enforcement.</dd>
</div>

<div>
<dt>MCP adapter</dt>
<dt><span className="stigmem-fields__type">adapter</span></dt>
<dd><code>assert_fact</code> and <code>query_facts</code> tool surface.</dd>
</div>

<div>
<dt>OpenClaw / Claude Code adapter</dt>
<dt><span className="stigmem-fields__type">adapter</span></dt>
<dd>Memory read/write paths.</dd>
</div>

</div>

### Out of scope

<div className="stigmem-fields">

<div>
<dt>Surface</dt>
<dt><span className="stigmem-fields__type">Reason</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Docs build toolchain</dt>
<dt><span className="stigmem-fields__type">build-time</span></dt>
<dd>Docusaurus, npm transitive deps. No user-controlled input path.</dd>
</div>

<div>
<dt>Third-party dependencies</dt>
<dt><span className="stigmem-fields__type">upstream</span></dt>
<dd>libSQL cloud, Turso, Postgres, Rekor. Report findings to the upstream project.</dd>
</div>

<div>
<dt>Rate limiting / resource exhaustion</dt>
<dt><span className="stigmem-fields__type">known gap</span></dt>
<dd>Tracked as a planned hardening item.</dd>
</div>

<div>
<dt>Social engineering / phishing</dt>
<dt><span className="stigmem-fields__type">universal</span></dt>
<dd>Out of scope for all security programs.</dd>
</div>

<div>
<dt><code>docs.stigmem.dev</code></dt>
<dt><span className="stigmem-fields__type">static</span></dt>
<dd>No user data; no dynamic server-side logic.</dd>
</div>

</div>

## Safe-harbor terms

If you conduct good-faith testing within the scope above, Eidetic Labs will not pursue legal action and will publicly credit you in `SECURITY.md` and the relevant release notes (unless you prefer anonymity).

<div className="stigmem-keypoint">

**"Good faith" means**

<div className="stigmem-grid">

<div><h4>No third-party data</h4><p>You do not access, exfiltrate, or modify data that is not yours.</p></div>
<div><h4>Your own instance</h4><p>You test against your own node or a dedicated test environment.</p></div>
<div><h4>Private before public</h4><p>You report findings privately before public disclosure.</p></div>
<div><h4>No DoS for others</h4><p>You do not cause service disruption to other users' nodes.</p></div>
<div><h4>Minimal exploitation</h4><p>You do not exploit a finding beyond what is necessary to confirm it exists.</p></div>

</div>

</div>

## Severity guidance

Use CVSS 4.0 as the primary severity signal.

<div className="stigmem-fields">

<div>
<dt>Severity</dt>
<dt><span className="stigmem-fields__type">Class</span></dt>
<dd>Examples</dd>
</div>

<div>
<dt>Critical</dt>
<dt><span className="stigmem-fields__type">9.0–10.0</span></dt>
<dd>Authentication bypass; remote code execution; federation peer impersonation; reading <code>local</code> or <code>team</code> facts without authorization.</dd>
</div>

<div>
<dt>High</dt>
<dt><span className="stigmem-fields__type">7.0–8.9</span></dt>
<dd>Privilege escalation; scope boundary bypass; replay-attack success; Source Attestation bypass in <code>enforce</code> mode.</dd>
</div>

<div>
<dt>Medium</dt>
<dt><span className="stigmem-fields__type">4.0–6.9</span></dt>
<dd>DoS with a clear exploit path; SSRF via federation pull path; information disclosure beyond error messages.</dd>
</div>

<div>
<dt>Low</dt>
<dt><span className="stigmem-fields__type">0.1–3.9</span></dt>
<dd>Minor information disclosure; non-critical config defaults that weaken posture.</dd>
</div>

<div>
<dt>Informational</dt>
<dt><span className="stigmem-fields__type">—</span></dt>
<dd>Defense-in-depth suggestions; hardening recommendations without a clear exploit.</dd>
</div>

</div>

## Advisory publication

Stigmem publishes GitHub Security Advisories for Critical and High CVSS 4.0 findings that affect a supported published artifact once a patched version is available. The v0.9.0a2 hardening release includes six Critical/High GHSAs.

```bash
pip install --upgrade --pre stigmem-node
# or, for the meta-package install:
pip install --upgrade --pre 'stigmem[node]'
```

<div className="stigmem-fields">

<div>
<dt>GHSA</dt>
<dt><span className="stigmem-fields__type">Severity · CVSS 4.0</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-jmfc-hfjq-pxcp">GHSA-jmfc-hfjq-pxcp</a></dt>
<dt><span className="stigmem-fields__type">Critical · 9.1</span></dt>
<dd>—</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-fp6w-8wpg-74g5">GHSA-fp6w-8wpg-74g5</a></dt>
<dt><span className="stigmem-fields__type">Critical · 9.2</span></dt>
<dd>—</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-9vp8-3hmv-8fgh">GHSA-9vp8-3hmv-8fgh</a></dt>
<dt><span className="stigmem-fields__type">Critical · 9.1</span></dt>
<dd>—</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-xh5j-xjfq-qvvx">GHSA-xh5j-xjfq-qvvx</a></dt>
<dt><span className="stigmem-fields__type">High · 7.1</span></dt>
<dd>—</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-w7pm-9g55-mxfm">GHSA-w7pm-9g55-mxfm</a></dt>
<dt><span className="stigmem-fields__type">High · 7.3</span></dt>
<dd>—</dd>
</div>

<div>
<dt><a href="https://github.com/eidetic-labs/stigmem/security/advisories/GHSA-9pc9-4crj-mhpj">GHSA-9pc9-4crj-mhpj</a></dt>
<dt><span className="stigmem-fields__type">High · 7.5</span></dt>
<dd>—</dd>
</div>

</div>

## Security posture — v0.9.0a2

<div className="stigmem-keypoint">

**Posture-reset note.**

The 2026-05-08 reset to `v0.9.0a1` carried forward the
dependency-fix posture from the withdrawn v1.0 release-candidate
snapshot. Several **threat-model** controls (mTLS-default federation,
persistent audit log, per-principal rate limits, capability-level
cross-org instruction validation, bounded HLC skew, the ADR-016
storage-immutability stack) remain future hardened-core work and are
**not yet in effect** at v0.9.0a2. Adopters running federation across
organizational boundaries should wait until those controls ship and
complete operator validation.

</div>

The dependency-alert posture carried forward to v0.9.0a2 has **zero unaddressed Dependabot alerts**:

<div className="stigmem-fields">

<div>
<dt>Category</dt>
<dt><span className="stigmem-fields__type">Count</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Dependabot alerts resolved</dt>
<dt><span className="stigmem-fields__type">20</span></dt>
<dd>By the dep upgrade sweep.</dd>
</div>

<div>
<dt>Docs build toolchain</dt>
<dt><span className="stigmem-fields__type">7</span></dt>
<dd>Non-exploitable, suppressed.</dd>
</div>

<div>
<dt>Unaddressed / escalated blockers</dt>
<dt><span className="stigmem-fields__type">0</span></dt>
<dd>—</dd>
</div>

</div>

### Security controls in effect

<div className="stigmem-fields">

<div>
<dt>Control</dt>
<dt><span className="stigmem-fields__type">Layer</span></dt>
<dd>Detail</dd>
</div>

<div>
<dt>Authentication</dt>
<dt><span className="stigmem-fields__type">API</span></dt>
<dd>API keys enforced on all write endpoints; per-scope restrictions (spec §3.5).</dd>
</div>

<div>
<dt>Federation</dt>
<dt><span className="stigmem-fields__type">protocol</span></dt>
<dd>Ed25519 peer handshake; HLC timestamps prevent replay attacks.</dd>
</div>

<div>
<dt>Input validation</dt>
<dt><span className="stigmem-fields__type">HTTP</span></dt>
<dd>Pydantic on all endpoints; malformed payloads return 422 before business logic.</dd>
</div>

<div>
<dt>Secrets</dt>
<dt><span className="stigmem-fields__type">repo</span></dt>
<dd>No credentials in the repository; Docker Compose uses env-var injection.</dd>
</div>

<div>
<dt>CI gate</dt>
<dt><span className="stigmem-fields__type">supply chain</span></dt>
<dd><code>pip-audit</code>, <code>pnpm audit</code>, and <code>bandit</code> run as blocking steps on every PR.</dd>
</div>

</div>

## Audit tooling

<div className="stigmem-fields">

<div>
<dt>Tool</dt>
<dt><span className="stigmem-fields__type">Scope</span></dt>
<dd>Gate</dd>
</div>

<div>
<dt><code>pip-audit</code></dt>
<dt><span className="stigmem-fields__type">Python deps</span></dt>
<dd><code>python-tests</code> job; exits non-zero on any moderate+ CVE.</dd>
</div>

<div>
<dt><code>pnpm audit</code></dt>
<dt><span className="stigmem-fields__type">Node.js deps</span></dt>
<dd><code>node-tests</code> job; <code>--audit-level=moderate</code>.</dd>
</div>

<div>
<dt><code>bandit</code></dt>
<dt><span className="stigmem-fields__type">Python static</span></dt>
<dd><code>python-tests</code> job; configured in <code>[tool.bandit]</code>.</dd>
</div>

</div>

**Run locally:**

```bash
# Python dependency audit
uv run pip-audit

# Python static security analysis
uv run bandit -r node/src/ sdks/stigmem-py/src/ -c pyproject.toml

# Node.js dependency audit
pnpm audit --audit-level=moderate
```

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

For federation testing, `docker-compose.federation.yml` spins up a 2-node topology:

```bash
docker compose -f docker-compose.federation.yml up -d
```

## Coordinated disclosure

The default window is **90 days** from acknowledgment of a valid finding.

<div className="stigmem-grid">

<div><h4>Actively exploited</h4><p>Faster coordination with reporter agreement.</p></div>
<div><h4>Straightforward fix</h4><p>Faster publication timeline communicated.</p></div>
<div><h4>90 days insufficient</h4><p>Extension discussed with the reporter.</p></div>

</div>

## Bug bounty

Stigmem does not currently operate a paid bug bounty program. Valid findings are recognized with:

<div className="stigmem-grid">

<div><h4>Public credit</h4><p>In <code>SECURITY.md</code> and the fixing release's changelog.</p></div>
<div><h4>Spec attribution</h4><p>In spec errata if the finding affects wire-format or protocol behavior.</p></div>

</div>

## See also

<div className="stigmem-grid">

<div><h4><a href="../security/pen-test.md">Community Pen-Test Handbook</a></h4><p>Full engagement guide with report template.</p></div>
<div><h4><a href="../security/container-hardening.md">Container Hardening</a></h4><p>Distroless, seccomp, non-root.</p></div>
<div><h4><a href="../security/key-rotation.md">Key Rotation</a></h4><p>Ed25519 key lifecycle and dual-trust windows.</p></div>
<div><h4><a href="../security/audit-and-quotas.md">Audit &amp; Quotas</a></h4><p>Audit log surface and per-principal rate limiting.</p></div>

</div>
