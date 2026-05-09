# LIMITATIONS

> **Stigmem v0.9.0a1.** Not yet suitable for production federation across organizational boundaries. Read this before deploying.
>
> Last updated: 2026-05-09 · Applies to: v0.9.0a1

---

## What this document is

A plain-English statement of what stigmem cannot safely do in its current state, organized by deployment scenario. It is the operator's companion to the formal [threat model](spec/security/threat-model.md) and the disclosure policy in [SECURITY.md](SECURITY.md).

If the threat model tells you *what the threats are*, this document tells you *what to actually do or not do today*. It is updated on every release. The contents below apply to **v0.9.0a1** specifically; future versions will close some of these gaps and may open new ones (each new feature lands with its own limitations entry).

If after reading this you're unsure whether your use case is safe, the answer is: ask in [Discussions](https://github.com/eidetic-labs/stigmem/discussions) before deploying. We'd rather lose an integration than have you hit one of these gaps in production.

---

## Current state in one sentence

Stigmem v0.9.0a1 is a working federated-memory reference node with a documented threat model and several controls our own threat model identifies as required for safe deployment that have not yet shipped. Those controls land during Phase B of the strengthening plan (see [ROADMAP.md](ROADMAP.md)). Until they do, the deployment recommendations below are the responsible defaults.

---

## What stigmem is **not** safe for today

These are unambiguous "do not" recommendations as of v0.9.0a1.

### 1. Cross-organizational federation in adversarial settings

**Status:** mTLS for federation peering is not on by default. Capability-token validation at admission is partial. HLC bounded-skew enforcement is not yet shipped. Per-peer drift tracking does not exist.

**What this means:** if you peer with a stigmem node operated by an organization you do not already fully trust, a malicious peer can:

- Impersonate a legitimate peer (no client-cert verification by default).
- Push HLC values forward to corrupt fact ordering across the federation.
- Replay capability tokens within a window we have not yet fuzz-tested adequately.
- Write instruction-shaped facts that flow into your agents' context without a structural quarantine boundary.

**What to do today:** do not federate across organizational boundaries until Phase B of the strengthening plan ships. Single-organization federation between nodes you operate yourself is safer, but still subject to the limitations below.

---

### 2. LLM agents holding admin-scope API keys

**Status:** No structural prevention. The adapter contract treats this as an "operator configuration" concern.

**What this means:** if an LLM-driven agent is configured with an admin-scope API key (for example, by mounting it into an MCP adapter), a successful prompt injection on that agent grants the attacker full administrative control of your stigmem node — manifest publishing, key rotation, quarantine override, all of it.

**What to do today:** never issue admin-scope keys to anything an LLM can drive. Admin keys are for human operators and automation under human supervision only. Agent keys should be scoped to the minimum necessary (typically `local` or `team`, write access only to the relations the agent specifically needs). We are working on a structural fix that refuses such configurations at the API layer (Phase B).

---

### 3. Treating recalled facts as instructions to your agent

**Status:** Our current prompt-injection defense (a recall-time content sanitizer that strips known injection sentinels) does not work against motivated adversaries. We know this. We are replacing it with a capability-based design (ADR-003) in the current sprint.

**What this means:** any fact written into a scope your agent reads from can attempt to inject instructions into the agent's context. The sanitizer catches obvious patterns and creates false confidence; novel injection patterns will pass through it.

**What to do today:** treat recalled fact `value` fields as untrusted external data, the same way you would treat a user-uploaded document. Specifically:

- Do not concatenate fact values directly into a system prompt without a clear, structurally-delimited "untrusted data" framing.
- Do not allow agents to act on instructions found in fact values without a separate authorization step that does not depend on the fact's content.
- If you build adapters that consume `recall()` output, frame the output as content, not instructions, and instruct the consuming LLM accordingly.

The capability-based redesign (where facts carry an `interpret_as` field that defaults to `"content"` and only flows as instructions with explicit operator authorization) lands in Phase B.

---

### 4. The agent feedback loop (read-injected → write-poisoned → replicate)

**Status:** Not currently mitigated. Not yet in the formal risk register; will be added as R-15 in the next threat-model revision.

**What this means:** an LLM-driven agent that has been prompt-injected by a recalled fact can use its own writer key to assert attacker-chosen facts back into the system. Those facts then look authoritative coming from your organization, and they replicate to your federation peers. This is the worm vector unique to federated agent memory.

**What to do today:**

- Restrict agent writer keys to the narrowest possible scope. Agents should not hold writer keys for any scope they also read from where they consume cross-org content, period.
- If your agent must both read company-scope facts and write company-scope facts, the read content must come from sources you trust (your own organization's writes, not federated peers).
- Review the [OpenClaw audit findings](#) (especially C4) before using the bundled OpenClaw adapter — the adapter currently has paths that exemplify this risk.

---

### 5. Storing regulated data without explicit at-rest encryption

**Status:** SQLCipher at-rest encryption is supported but **not on by default**.

**What this means:** the default deployment writes facts to a plaintext SQLite file. Anyone with read access to the disk can read all facts.

**What to do today:** if you are storing PHI, PII, financial data, or anything else governed by regulation, you must explicitly enable SQLCipher per the [hardening guide](docs/security/hardening.md). The default setup is not appropriate for regulated workloads.

---

### 6. Cloud embedding with sensitive fact content

**Status:** Cloud embedding (OpenAI, Cohere, etc.) is opt-in. The default deployment uses a local `nomic-embed-text-v1.5` model and never sends fact content to third parties.

**What this means:** if you opt into cloud embedding, **every fact's `entity + relation + value` string is sent to the embedding provider** during recall pipeline operation. Embedding providers may log, cache, or use that data per their terms of service.

**What to do today:** keep cloud embedding off for any deployment that handles sensitive data. If you need cloud embedding for performance or quality reasons, classify your data first and ensure your provider's terms align with your data-handling requirements. We do not yet check returned embeddings for adversarial manipulation by a hostile provider; that is a separate open risk (will be tracked in the next threat-model revision).

---

### 7. Production deployments without rate limits or audit logs

**Status:** Per-principal rate limits are not yet enforced. The audit log exists conceptually but is not yet WAL-ordered or persistent across the 13 documented event types.

**What this means:**

- A compromised API key can issue unbounded writes/recalls until you notice and rotate.
- A misbehaving agent can exhaust your storage or your CPU.
- You cannot reconstruct who-did-what from logs in a way suitable for incident response.

**What to do today:** treat v0.9.0a1 as a development and evaluation release. Production deployment is not recommended until Phase B of the strengthening plan completes (rate limits + persistent audit log). If you must deploy to production now, run behind a reverse proxy with its own rate limiting, and pipe stigmem's structured output to a SIEM you trust.

---

### 8. Long-lived API keys with weak hashing and no rotation

**Status (corrected 2026-05-09):** API keys are currently hashed at rest with raw SHA-256 (`node/src/stigmem_node/auth.py:_hash_key`). That's a fast, unsalted, parallelizable hash — fine for fact content addressing (where determinism is the point — see CIDs at §25), wrong for credential storage (where slowness + per-key salt are the point). ADR-007 commits to migrating API key hashing to Argon2id during Phase B; the migration itself has not landed. **Separately:** there is no enforced max-age, no automated rotation, no "expiring soon" surface.

**What this means:** an attacker who obtains the api_keys table (e.g., via R-23 admin-level storage compromise, or via a separate exfiltration vector) can mount a fast offline brute-force attack against the key hashes. Compounding: keys live forever unless rotated manually, and you have no system reminder when one becomes stale.

**What to do today:**

- **Treat the api_keys table as a high-value secret.** Restrict filesystem access to it. Don't back it up in clear-text. If you're using SQLCipher (`STIGMEM_AT_REST_KEY_PASSPHRASE_ENV` set — see Limitation 5), the table is encrypted at rest with an Argon2id-derived key, which substantially raises the bar — recommended for any deployment with regulated data or sensitive workloads.
- **Generate API keys at sufficient length** (the default is 256-bit; don't override to anything shorter). At 256 bits of entropy, even a fast SHA-256 attacker is fundamentally bounded; the hash weakness matters more for *short* or *predictable* keys.
- **Rotate keys manually on your own schedule** (recommend ≤90 days). Treat any key issued for testing or demo purposes as compromised once you've shared it with anyone outside the issuance context.

Phase B brings: Argon2id migration with backward-compatible verification (per ADR-007), enforced max-age, automated rotation runbooks, and an "expiring soon" admin surface.

**Why this wasn't caught earlier:** an earlier draft of this section said "Argon2id-hashed at rest (good)" — that was wrong; the code uses raw SHA-256. Caught and corrected during pre-publish gate review for v0.9.0a1.

---

### 9. Running the OpenClaw bundled adapter as-is

**Status:** Several critical issues identified in audit (see `stigmem/openclaw/audit.md` in the repo). Some require ADR-003 to land before they can be fully fixed.

**What this means:** the OpenClaw adapter, in its v0.9.0a1 state, has a documented prompt-injection surface, an unvalidated handoff target (worm vector), partial-write semantics on multi-fact handoffs, and several other issues.

**What to do today:** treat the OpenClaw adapter as `experimental/`. If you've integrated against it, read the audit findings before deciding whether to keep the integration in production. The hardened adapter ships during the capability-redesign work in Phase B of the strengthening plan.

---

### 10. Federation patterns not supported by the four-scope model

**Status:** The current scope model (`local` / `team` / `company` / `public`) is sufficient for single-organization deployments and trusted bilateral peering. It does not express several federation patterns that operators with multi-org or coalition deployments may need. Richer expressivity is planned for v1.x via memory gardens (currently experimental, see `Spec-X5`).

**What this means:** the following federation patterns are **not** supported in v0.9.0a1 and require either custom integration on top of stigmem or waiting for the basic memory-garden primitive to graduate from experimental:

- **Selective sharing with specific peers.** No way to express "shared with Partner Org B but not Partner Org C." Workaround: use `public` (over-shares to every peer) or run separate stigmem deployments per peering relationship.
- **Coalition or consortium membership.** No way to express a multi-org shared scope (e.g., a three-university research consortium). Workaround: separate stigmem deployment for the coalition.
- **Asymmetric trust between peers.** Trust is symmetric per peering agreement; capability tokens authorize *write* asymmetry but the four-scope model does not express *visibility* asymmetry between peers.
- **Project-bounded collaboration.** No way to express a per-project shared scope across orgs (e.g., "facts about Joint Project X are visible to both Org A and Org B; everything else stays internal"). Workaround: separate deployment per project.
- **Hierarchical organization relationships.** No native parent-subsidiary modeling. Each org is independent in the federation graph; a parent company cannot natively express "share these facts with all my subsidiaries but not external peers."
- **Compliance-aware scopes.** Regulated data (PHI, PII, financial) must be handled by operator-layer policy. The scope model is not compliance-aware; operators must layer classification, retention, and audit-trail requirements on top.
- **Time-bounded shared scopes.** Per-fact `valid_until` covers fact-level expiry; the four-scope model does not express "this scope's contents are visible to peer X for time T."
- **Read-vs-write asymmetry per peer at the scope level.** Capability tokens distinguish read from write at the verb level, but combining scope + token to express "Peer B can read scope X, but not write to it" is awkward and requires careful operator configuration.

**What to do today:** if your federation use case is single-organization or trusted bilateral peering, the four-scope model is sufficient. For coalition, multi-peer, or project-bounded patterns, evaluate whether stigmem v0.9.0a1 meets your needs before deploying. The basic memory-garden primitive that addresses these patterns is targeted for v1.x once `Spec-X5` graduates from experimental via the ADR-008 gate process. Operators with these requirements who want to influence prioritization should [open an issue](https://github.com/eidetic-labs/stigmem/issues) tagged `area/federation-expressivity`.

**Why we chose this for v0.9.0a1:** expanding the scope model in v1.0 would be exactly the kind of scope churn ADR-002 is designed to prevent. The decision is to ship the smaller defensible thing (four scopes, simple federation) and grow expressivity through gardens once they pass the ADR-008 gates. The full analysis is in `stigmem-scope-model-analysis.md`.

---

## Install footguns specific to v0.9.0a1

These are pre-release-era install behaviors that surprise adopters who don't expect them. Each is the *correct* behavior for a pre-stable release; documenting so the surprise is named, not eliminated.

### `pip install stigmem` returns "no matching distribution found"

**Cause:** v0.9.0a1 is a PEP 440 pre-release (`a1` = alpha 1). `pip` excludes pre-releases from default resolution; it returns a "no matching distribution found" error rather than installing the alpha.

**Fix:** add `--pre`:

```bash
pip install --pre stigmem            # SDK only (default)
pip install --pre stigmem[node]      # SDK + reference node service
pip install --pre stigmem[all]       # everything published from this monorepo
```

This is intentional — adopters running `pip install <pkg>` in CI shouldn't accidentally pull in pre-stable software. It will go away when v1.0 ships (no `--pre` needed for stable releases).

### `stigmem` is a meta-package, not the actual code

**What you get:** `pip install --pre stigmem` installs an empty wheel called `stigmem` plus its declared dependency `stigmem-py>=0.9.0a1,<1.0.0`. The actual SDK code is in `stigmem-py`. Adopters who run `pip show stigmem` see ~5 metadata files and no Python source — that's correct.

**Why:** the canonical name `stigmem` should resolve to a useful install. Most adopters want the SDK (the most common use case in client/server software). Operators self-hosting want the server, available via `stigmem[node]` or `pip install --pre stigmem-node` directly. Mirrors the pattern of `redis`/`psycopg`/`elasticsearch` — bare-name install always = client SDK.

**If you want the actual SDK code path:** `import stigmem` in Python imports from `stigmem-py`'s installed location. The meta-package's empty wheel doesn't intercept anything.

### npm SDK is scoped under `@eidetic-labs`

**What works:**
```bash
npm install @eidetic-labs/stigmem-ts          # ⚠ no version: gets the LATEST stable, which is currently nothing
npm install @eidetic-labs/stigmem-ts@alpha    # gets the latest 0.9.0-alpha.* prerelease
npm install @eidetic-labs/stigmem-ts@0.9.0-alpha.1   # explicit pin
```

**Why scoped:** npm's free-tier organization permissions don't allow team-bound package access controls; scoping under `@eidetic-labs` sidesteps that limitation entirely.

**The `@alpha` dist-tag is required during the v0.9.0a* line.** Bare `npm install` resolves the `latest` tag, which won't exist until v1.0 ships. This is the npm equivalent of pip's `--pre` flag — same intent, different syntax.

### Pre-release packages don't auto-upgrade

**What this means:** if you pin to `stigmem==0.9.0a1` and we publish `0.9.0a2` next week, `pip install --upgrade stigmem` won't pick up `a2` unless you also pass `--pre`. Same for npm: `npm update @eidetic-labs/stigmem-ts` won't pick up the new alpha unless you `npm install @eidetic-labs/stigmem-ts@alpha` (which always tracks the latest alpha).

**Recommendation:** during the v0.9.0a* and v0.9.0b* phase, explicitly pin or explicitly request the dist-tag. Auto-upgrade is unsafe for pre-stable software anyway — we may break the wire format between alphas.

---

## What stigmem **is** reasonable for today

These are use cases where v0.9.0a1 is genuinely useful and the limitations above don't materially affect you:

### Single-node, single-organization, non-regulated experimentation

Running one stigmem node on your own infrastructure, populated by your own agents and tools, with no federation peers — this is the use case the current code base supports well. Recall works, scopes are enforced at the SQL layer, the typed-fact model with provenance is functional, and the local-only deployment removes most of the federation-specific risks above.

### Local development and prototyping

Developers building agent applications who want to evaluate whether typed-fact memory is the right shape for their problem. Pin to a specific v0.9.x version, expect breaking changes during the Phase B hardening window, and treat the data as throwaway.

### Internal tooling within a single trust boundary

Memory for developer tools, internal agents, and automation that lives entirely inside your organization's existing security perimeter, where the adversary model is "honest mistakes by colleagues" rather than "active attacker." The single-organization default is reasonable for this audience.

### Threat-model evaluation

Reading our threat model, comparing it to your own requirements, and giving us feedback. This is genuinely the most valuable thing the broader community can do for the project right now. The [threat model](spec/security/threat-model.md) and the [risk register](spec/security/threat-model.md#7-risk-register) are open for issue-by-issue scrutiny.

---

## What we recommend right now

### If you are evaluating stigmem

Read this document, read the threat model, run `make demo` locally, and decide whether the design fits your problem. Don't deploy yet.

### If you have already integrated against v1.0

Your code does not need to change today; the wire format hasn't changed. **Do not deploy in cross-org federation configurations.** Pin to v0.9.0a1 and expect minor breaking changes during Phase B of the strengthening plan. Read the [retraction post](#) for context on the version change.

### If you want to be our first external operator

We're looking for one organization willing to run a stigmem node for 30 days against a real (non-critical) workload, with public bug reporting. We'll help you set up, watch you hit issues we couldn't anticipate, and credit you in the v1.0 release notes. [Open an issue](https://github.com/eidetic-labs/stigmem/issues) tagged `operator-candidate`.

### If you are auditing the security posture

Start with the [threat model](spec/security/threat-model.md). Cross-reference findings here. File issues for anything we've missed. Especially welcome: scenarios we haven't modeled, attacks our risk register doesn't cover, controls we claim that aren't actually enforced in code.

---

## Closing the gaps

The strengthening plan in `stigmem/plans/strengthening-plan.md` is the public sequencing for closing the gaps named above. A condensed view, by phase:

| Limitation | Closes in | Tracked as |
|---|---|---|
| Cross-org federation safety (mTLS-default, HLC bounds, capability validation) | Phase B (federation hardening) | R-01, R-14, R-16 |
| Prompt-injection structural defense | Phase B (capability redesign) | R-05 (replaces sanitizer with capability model) |
| Agent feedback-loop attack | Phase B (capability redesign) | R-15 (new) |
| Persistent audit log | Phase B (federation hardening) | R-09 |
| Per-principal rate limits | Phase B (federation hardening) | R-02 |
| API key max-age & rotation | Phase B (federation hardening) | R-03 |
| OpenClaw adapter hardening | Phase B (capability redesign) | OpenClaw audit C-series |
| At-rest encryption defaults | Phase C (v1.0.0 GA) | R-04 |
| Embedding poisoning detection | Phase D (post-v1.0) | new entry |
| Federation expressivity (selective peer sharing, coalitions, project scopes) | Phase D (gardens via ADR-008 gates) | Spec-X5 |

After Phase B ships and a 30-day operator soak completes, this document will be updated to reflect what is actually safe in v1.0, what remains opt-in, and what is still on the roadmap.

---

## How to read this document over time

Every release of stigmem ships with an updated LIMITATIONS.md. Each entry has one of three lifecycle states:

- **Open** — the limitation is real for this version. Follow the "What to do today" guidance.
- **Closed** — the underlying risk has been mitigated. The entry is removed from this document and a `CHANGELOG.md` entry records the closure with a link to the relevant PR or ADR.
- **Accepted** — we have decided not to mitigate, with stated rationale. The entry stays in this document indefinitely with a "Why we accept this" note.

If a limitation moves from Open to Closed in your installed version, you can read the threat-model risk register's status column to confirm. If you find a behavior in production that this document doesn't cover, please open an issue tagged `limitations-doc`. Documents like this one are only useful when they're complete, and we cannot be complete without your reports.

---

— Eidetic Labs · [github.com/eidetic-labs/stigmem](https://github.com/eidetic-labs/stigmem)
