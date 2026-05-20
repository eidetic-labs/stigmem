---
title: Community Pen-Test Handbook
sidebar_label: Pen-Test Handbook
description: Everything a security researcher or pen tester needs to run a structured engagement against Stigmem — scope, safe harbor, reproducer expectations, report template, and recognition.
audience: Operator
---

# Community Pen-Test Handbook

<p className="stigmem-meta"><span>7 min read</span><span>Security researcher · Penetration tester · Protocol reviewer</span><span>Coordinated disclosure</span></p>

<div className="stigmem-lead">

**What this page is**

Stigmem is an open federated protocol. External security scrutiny
makes it stronger. This handbook covers everything you need to run a
structured engagement — from scoping your test to getting your
findings in front of the maintainers.

</div>

For the project's vulnerability disclosure policy and supported-version
matrix, see [`SECURITY.md`](https://github.com/eidetic-labs/stigmem/blob/main/SECURITY.md).
For the technical threat model, see [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

## 1 · In-scope targets

The following surfaces are explicitly in scope for community pen
testing.

<div className="stigmem-fields">

<div>
<dt>Surface</dt>
<dt><span className="stigmem-fields__type">Coverage</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Reference node HTTP API</dt>
<dt><span className="stigmem-fields__type">all endpoints</span></dt>
<dd><code>/v1/facts</code>, <code>/v1/query</code>, <code>/v1/recall</code>, <code>/v1/cards/&#42;</code>, <code>/v1/graph/&#42;</code>, <code>/v1/synthesis</code>, <code>/v1/decay</code>, <code>/v1/conflicts</code>, <code>/v1/subscriptions</code>, <code>/v1/federation/&#42;</code>, <code>/v1/admin/&#42;</code>. Authenticated and unauthenticated paths; read and write surfaces.</dd>
</div>

<div>
<dt>Federation handshake and replication</dt>
<dt><span className="stigmem-fields__type">protocol</span></dt>
<dd>PeerDeclaration signing, HLC cursor handling, replay protection, capability token validation.</dd>
</div>

<div>
<dt>Authentication and API key lifecycle</dt>
<dt><span className="stigmem-fields__type">identity</span></dt>
<dd>Key issuance, storage (Argon2id hashing), validation, scope enforcement, revocation.</dd>
</div>

<div>
<dt>Capability token issuance and validation</dt>
<dt><span className="stigmem-fields__type">crypto</span></dt>
<dd>Ed25519 signing, expiry, nonce, verb/object scope enforcement (Spec-06-Capability-Tokens).</dd>
</div>

<div>
<dt>Source Attestation</dt>
<dt><span className="stigmem-fields__type">Spec-X6</span></dt>
<dd>Enforcement modes (<code>enforce</code>, <code>warn</code>, <code>off</code>); entity-URI binding.</dd>
</div>

<div>
<dt>Memory Garden ACLs</dt>
<dt><span className="stigmem-fields__type">Spec-02</span></dt>
<dd>Role escalation paths; garden boundary enforcement; quarantine admit/release.</dd>
</div>

<div>
<dt>MCP adapter</dt>
<dt><span className="stigmem-fields__type">integration</span></dt>
<dd><code>assert_fact</code>, <code>query_facts</code>, <code>recall</code>, <code>lint_scope</code> tool surface.</dd>
</div>

<div>
<dt>OpenClaw / Claude Code adapter</dt>
<dt><span className="stigmem-fields__type">integration</span></dt>
<dd>Memory read/write paths.</dd>
</div>

<div>
<dt>Recall pipeline</dt>
<dt><span className="stigmem-fields__type">Spec-07 + Spec-X11</span></dt>
<dd>Scope isolation across lexical, vector, and graph stages.</dd>
</div>

<div>
<dt>Audit log endpoints</dt>
<dt><span className="stigmem-fields__type">pre-reset hardening</span></dt>
<dd>Access control on <code>/v1/admin/audit-log</code>; log tamper-resistance.</dd>
</div>

<div>
<dt>Per-principal quota enforcement</dt>
<dt><span className="stigmem-fields__type">pre-reset hardening</span></dt>
<dd>Correct application of token-bucket ceilings; bypass attempts.</dd>
</div>

</div>

### Priority finding categories

The following finding classes are of the highest interest to
maintainers.

<div className="stigmem-grid">

<div><h4>Authentication bypass</h4><p>Accessing write endpoints without a valid API key, or escalating a <code>public</code>-scoped key to read/write <code>team</code> or <code>local</code> facts.</p></div>
<div><h4>Cross-org data leakage</h4><p>A capability token or API key granting access to facts beyond its declared scope.</p></div>
<div><h4>Federation peer impersonation</h4><p>Successfully acting as a peer node without a valid mTLS certificate and matching org manifest.</p></div>
<div><h4>Capability token replay or forgery</h4><p>Replaying a revoked token, forging a signature, or bypassing the nonce/timestamp window.</p></div>
<div><h4>Prompt injection via recall</h4><p>Bypassing the recall-time content sanitizer (ADR-003 defense-in-depth) to inject instructions into an LLM context via stored fact values.</p></div>
<div><h4>Quarantine garden bypass</h4><p>Causing an untrusted fact to enter the main fact store without passing through quarantine review.</p></div>
<div><h4>Source Attestation bypass</h4><p>Writing facts without a valid attestation in <code>enforce</code> mode.</p></div>

</div>

## 2 · Out-of-scope targets

Testing these will **not result in credit** and may violate
third-party terms of service.

<div className="stigmem-fields">

<div>
<dt>Surface</dt>
<dt><span className="stigmem-fields__type">Reason</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>https://docs.stigmem.dev</code></dt>
<dt><span className="stigmem-fields__type">static site</span></dt>
<dd>No user data; no dynamic server-side logic.</dd>
</div>

<div>
<dt>Docs build toolchain</dt>
<dt><span className="stigmem-fields__type">build-time only</span></dt>
<dd>Docusaurus, npm transitive deps. No user-controlled input path in the deployed docs site.</dd>
</div>

<div>
<dt>Third-party dependencies</dt>
<dt><span className="stigmem-fields__type">upstream</span></dt>
<dd>libSQL cloud, Turso, PostgreSQL, Rekor/Sigstore. Report findings to the upstream project directly.</dd>
</div>

<div>
<dt>Third-party nodes not operated by you</dt>
<dt><span className="stigmem-fields__type">authorization</span></dt>
<dd>You must only test against nodes you operate or have explicit permission to test.</dd>
</div>

<div>
<dt>Rate limiting / resource exhaustion with no exploit path</dt>
<dt><span className="stigmem-fields__type">known gap</span></dt>
<dd>Use <code>fact_write</code> quota dimension (pre-reset hardening) to test post-hardening.</dd>
</div>

<div>
<dt>Social engineering or phishing</dt>
<dt><span className="stigmem-fields__type">scope policy</span></dt>
<dd>Out of scope for all security programs.</dd>
</div>

<div>
<dt>Physical access to infrastructure</dt>
<dt><span className="stigmem-fields__type">N/A</span></dt>
<dd>Not applicable to community testers.</dd>
</div>

</div>

## 3 · Safe-harbor terms

If you conduct good-faith testing **within the scope above**, Eidetic
Labs will not pursue legal action and will publicly credit you in
`SECURITY.md` and the relevant release notes (unless you prefer
anonymity).

<div className="stigmem-keypoint">

**"Good faith" means**

</div>

<ol className="stigmem-steps">
<li>You do not access, exfiltrate, or modify data that is not yours.</li>
<li>You test against your own node instance or a dedicated test environment — not a third-party node without explicit written permission from that operator.</li>
<li>You report findings privately before public disclosure (see <a href="#8-disclosure-timeline">§8 Disclosure timeline</a>).</li>
<li>You do not cause service disruption to other operators or their users.</li>
<li>You do not exploit a finding beyond what is necessary to confirm it exists.</li>
<li>You do not automate requests at a rate that would degrade a shared test environment.</li>
</ol>

Violating any of the above conditions voids the safe-harbor commitment
for that engagement.

## 4 · Setting up a test environment

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

For a **4-node federation soak** including backpressure and
scope-propagation invariants, see the
[Federation: 4-Node Soak guide](../concepts/federation/federation-4node).

### Recommended test matrix

<div className="stigmem-fields">

<div>
<dt>Test area</dt>
<dt><span className="stigmem-fields__type">Setup</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>API auth / scope</dt>
<dt><span className="stigmem-fields__type">single node</span></dt>
<dd>Multiple keys with different scopes.</dd>
</div>

<div>
<dt>Federation peer auth</dt>
<dt><span className="stigmem-fields__type">2-node Compose</span></dt>
<dd>Topology.</dd>
</div>

<div>
<dt>Capability token replay</dt>
<dt><span className="stigmem-fields__type">single node</span></dt>
<dd>Issue + replay with modified nonce/timestamp.</dd>
</div>

<div>
<dt>Recall pipeline scope isolation</dt>
<dt><span className="stigmem-fields__type">single node</span></dt>
<dd>Facts asserted in mixed scopes; queries from lower-privilege key.</dd>
</div>

<div>
<dt>Prompt injection via recall</dt>
<dt><span className="stigmem-fields__type">single node</span></dt>
<dd>Adversarial fact values; recall via MCP adapter.</dd>
</div>

<div>
<dt>Quarantine bypass</dt>
<dt><span className="stigmem-fields__type">2-node topology</span></dt>
<dd>Assert from low-trust peer; inspect quarantine.</dd>
</div>

</div>

## 5 · Reproducer expectations

Every finding submitted via GitHub private advisory should include a
**self-contained reproducer**. Findings without a working reproducer
will be triaged as "needs more info" and may not receive credit until
one is provided.

<div className="stigmem-grid">

<div><h4>Environment</h4><p>Stigmem version/commit, backend type (SQLite/libSQL/Postgres), OS.</p></div>
<div><h4>Setup steps</h4><p>Exact commands to provision a test node and any required keys or data.</p></div>
<div><h4>Attack steps</h4><p>The exact request sequence, including all HTTP headers and bodies, in order.</p></div>
<div><h4>Expected behavior</h4><p>What should happen if the control is working correctly.</p></div>
<div><h4>Observed behavior</h4><p>What actually happened (HTTP response, data returned, side effect).</p></div>
<div><h4>Impact assessment</h4><p>What an attacker gains; whose data; what privilege level; can it pivot.</p></div>

</div>

**Example reproducer for a hypothetical scope bypass:**

```
Environment: stigmem the pre-reset v1.0-rc snapshot, SQLite backend, Docker Compose
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

## 6 · Report template

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
[e.g., the pre-reset v1.0-rc snapshot, all versions up to commit abc1234]

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

## 7 · Severity guidance

Use CVSS v3.1 as the primary severity signal. For Stigmem-specific
surfaces:

<div className="stigmem-fields">

<div>
<dt>Severity</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Examples</dd>
</div>

<div>
<dt><strong>Critical</strong></dt>
<dt><span className="stigmem-fields__type">total compromise</span></dt>
<dd>Authentication bypass; remote code execution; federation peer impersonation; reading <code>local</code> or <code>team</code> facts without authorization; capability token forgery.</dd>
</div>

<div>
<dt><strong>High</strong></dt>
<dt><span className="stigmem-fields__type">boundary breach</span></dt>
<dd>Privilege escalation within the API; scope boundary bypass (reading <code>local</code> facts via a <code>public</code> query path); replay-attack success against the federation handshake; Source Attestation bypass in <code>enforce</code> mode.</dd>
</div>

<div>
<dt><strong>Medium</strong></dt>
<dt><span className="stigmem-fields__type">exploitable issue</span></dt>
<dd>Denial-of-service with a clear exploit path (e.g., memory exhaustion via crafted federation payload); SSRF via the federation replication pull path; information disclosure beyond minor error messages; quarantine garden bypass.</dd>
</div>

<div>
<dt><strong>Low</strong></dt>
<dt><span className="stigmem-fields__type">minor</span></dt>
<dd>Minor information disclosure (e.g., internal stack traces in error responses); non-critical config defaults that weaken security posture.</dd>
</div>

<div>
<dt><strong>Informational</strong></dt>
<dt><span className="stigmem-fields__type">advisory</span></dt>
<dd>Defense-in-depth suggestions; hardening recommendations without a clear exploit path; deviations from best practice with no immediate impact.</dd>
</div>

</div>

## 8 · Disclosure timeline

The Stigmem project follows **coordinated disclosure** with a default
window of **90 days** from acknowledgment of a valid finding.

<div className="stigmem-fields">

<div>
<dt>Event</dt>
<dt><span className="stigmem-fields__type">Target SLA</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Initial acknowledgment</dt>
<dt><span className="stigmem-fields__type">48 hours</span></dt>
<dd>From receipt.</dd>
</div>

<div>
<dt>Scope / validity confirmation</dt>
<dt><span className="stigmem-fields__type">7 days</span></dt>
<dd>From receipt.</dd>
</div>

<div>
<dt>Patch target (Critical / High)</dt>
<dt><span className="stigmem-fields__type">14 days</span></dt>
<dd>From confirmation.</dd>
</div>

<div>
<dt>Patch target (Medium)</dt>
<dt><span className="stigmem-fields__type">45 days</span></dt>
<dd>From confirmation.</dd>
</div>

<div>
<dt>Patch target (Low / Informational)</dt>
<dt><span className="stigmem-fields__type">next release</span></dt>
<dd>Scheduled.</dd>
</div>

<div>
<dt>Coordinated public disclosure</dt>
<dt><span className="stigmem-fields__type">90 days</span></dt>
<dd>From acknowledgment (default).</dd>
</div>

</div>

**Exceptions to the 90-day window:**

<div className="stigmem-grid">

<div><h4>Actively exploited in the wild</h4><p>We coordinate with you and may disclose sooner, potentially within 7 days.</p></div>
<div><h4>Straightforward fix available</h4><p>We target faster publication and will communicate the updated timeline.</p></div>
<div><h4>90 days is insufficient</h4><p>If a patch requires architectural changes that take longer, we will discuss an extension with you. We will not request an extension more than once without a concrete timeline.</p></div>

</div>

We keep reporters informed of patch progress and release dates
throughout the window. If you have not heard from us within 7 days of
filing, ping the advisory thread directly.

## 9 · Coordinating a structured engagement

If you want to run a structured pen test (vs. individual ad-hoc
finding reports), open a
[GitHub Discussion](https://github.com/eidetic-labs/stigmem/discussions) with:

<div className="stigmem-grid">

<div><h4>Intended scope</h4><p>Which API surfaces, which spec version, which trust boundary.</p></div>
<div><h4>Test environment setup</h4><p>Your own node, isolated network, etc.</p></div>
<div><h4>Proposed timeline</h4></div>
<div><h4>Active-hardening context</h4><p>Anything you'd like to know about (e.g., "we're hardening TB-2 in pre-reset hardening — here's what's already in flight").</p></div>

</div>

Maintainers will confirm scope, share any active-hardening context,
and coordinate acknowledgment and credit at the end of your
engagement.

## 10 · Known hardening gaps

The following are **known gaps** planned for the pre-reset hardening
work (carried forward to v0.9.0a1). You are welcome to test and
report them — findings in this list will be triaged as **known**
rather than novel, but **novel attack paths** against them are still
valuable findings and eligible for full credit.

<div className="stigmem-fields">

<div>
<dt>Gap</dt>
<dt><span className="stigmem-fields__type">v0.9.0bN target</span></dt>
<dd>Spec reference</dd>
</div>

<div>
<dt>mTLS for federation peer connections (currently TLS only, no client cert)</dt>
<dt><span className="stigmem-fields__type">Spec-10-Hardening</span></dt>
<dd>mTLS + TLS 1.3 floor + SAN/entity_uri binding.</dd>
</div>

<div>
<dt>API-key rotation edge cases</dt>
<dt><span className="stigmem-fields__type">Spec-10-Hardening</span></dt>
<dd>Exercise enforced max-age, expiring-soon visibility, and revocation behavior.</dd>
</div>

<div>
<dt>Per-principal write/recall rate limits: not enforced</dt>
<dt><span className="stigmem-fields__type">Spec-10-Hardening</span></dt>
<dd>Token-bucket quotas on 7 dimensions.</dd>
</div>

<div>
<dt>Audit log: not yet shipped</dt>
<dt><span className="stigmem-fields__type">Spec-09-Audit-Log</span></dt>
<dd>13-event-type audit log, WAL ordering, 90-day retention.</dd>
</div>

<div>
<dt>Container runs as non-root but not distroless</dt>
<dt><span className="stigmem-fields__type">Spec-10-Hardening</span></dt>
<dd>Distroless base, read-only fs, dropped capabilities.</dd>
</div>

<div>
<dt>Federation replay-protection fuzz test coverage</dt>
<dt><span className="stigmem-fields__type">Spec-11-Replay-Protection</span></dt>
<dd>Fuzz tests + HLC + nonce end-to-end verification.</dd>
</div>

<div>
<dt>Constant-time crypto: audit pending</dt>
<dt><span className="stigmem-fields__type">cryptography</span></dt>
<dd>Full constant-time audit of Ed25519 path.</dd>
</div>

</div>

The full threat model with STRIDE analysis per trust boundary lives
at [`spec/security/threat-model.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md).

## 11 · Recognition

Stigmem does not currently operate a paid bug bounty program. Valid
findings are recognized with:

<div className="stigmem-grid">

<div><h4>Hall of fame</h4><p>Your name or handle is added to the <code>SECURITY.md</code> acknowledgments section and the fixing release's changelog.</p></div>
<div><h4>Attribution in the spec errata</h4><p>If your finding affects wire-format or protocol behavior, you are credited in the relevant modular spec changelog as a contributor to that revision.</p></div>
<div><h4>Coordinated disclosure credit</h4><p>The GitHub Security Advisory, when published, lists you as the reporter.</p></div>

</div>

If you prefer to remain anonymous, say so in your report template
(`[ ] I prefer anonymous credit`) and we will honor that throughout
all public communications.

This recognition model may evolve as the project scales.
