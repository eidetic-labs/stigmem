---
title: Protocol Design Decisions
sidebar_label: Design Decisions
audience: Spec
description: "Protocol design decisions retained as overview prose."
---

# Protocol Design Decisions \{#section-7\}

<p className="stigmem-meta"><span>2 min read</span><span>Spec contributor · Reviewer</span><span>Overview prose</span></p>

<div className="stigmem-lead">

**What this page is**

Why the spec made the calls it did — federation, contradictions,
entity-vs-agent scoping. Overview prose retained from the v0.9.0a1
specification lineage; design decisions are not an independent
component spec.

</div>

**Authoritative source:**
[`spec/stigmem-spec-v0.9.0a1.md`](https://github.com/eidetic-labs/stigmem/blob/main/spec/stigmem-spec-v0.9.0a1.md)

:::note Section body
Each subsection below shows the most recent normative text from the
spec source. When earlier spec drafts also contained text for the
same subsection, those revisions are collapsed under a `Revisions`
accordion beneath it.
:::

## Active decisions

<div className="stigmem-fields">

<div>
<dt>Decision</dt>
<dt><span className="stigmem-fields__type">Area</span></dt>
<dd>Rationale</dd>
</div>

<div>
<dt>Garden as partition above scope</dt>
<dt><span className="stigmem-fields__type">scopes & ACL</span></dt>
<dd>Scope is coarse (4 values); gardens add named, member-gated segmentation without replacing the scope model. Gardens sit inside a scope, not in place of it.</dd>
</div>

<div>
<dt>Garden membership is node-local</dt>
<dt><span className="stigmem-fields__type">federation</span></dt>
<dd>Cross-node garden federation introduces complex identity delegation questions (who validates remote membership?). Deferred to the pre-reset attestation-chain work when the federation model matures.</dd>
</div>

<div>
<dt><code>garden_id</code> field on fact, not a separate collection</dt>
<dt><span className="stigmem-fields__type">data model</span></dt>
<dd>Facts remain the canonical storage primitive. <code>garden_id</code> is a tag that the node enforces at ACL time. No schema redesign needed.</dd>
</div>

<div>
<dt>Orphaned facts on garden delete</dt>
<dt><span className="stigmem-fields__type">lifecycle</span></dt>
<dd>Deleting facts on garden delete would be a destructive non-reversible action. Facts are immutable; orphan detection via lint is the safer path.</dd>
</div>

<div>
<dt>Source attestation at node, not client</dt>
<dt><span className="stigmem-fields__type">trust</span></dt>
<dd>Attestation by client is trivially forgeable. Binding at the node, using the verified identity from the Bearer token, is the only trustworthy enforcement point.</dd>
</div>

<div>
<dt>Three attestation modes (<code>enforce</code>/<code>warn</code>/<code>off</code>)</dt>
<dt><span className="stigmem-fields__type">migration</span></dt>
<dd>Single-operator self-hosted deployments must not break when upgrading. <code>warn</code> default gives operators time to audit before enforcing.</dd>
</div>

<div>
<dt>No delegated attestation in the pre-reset spec</dt>
<dt><span className="stigmem-fields__type">scope cut</span></dt>
<dd>Service-agent-writes-for-human is a real pattern, but the delegation chain (who authorized whom) requires a richer identity model. Track C of the pre-reset substrate work adds per-agent keypairs; delegation attestation follows.</dd>
</div>

<div>
<dt><code>attested: null</code> for federation ingest</dt>
<dt><span className="stigmem-fields__type">provenance</span></dt>
<dd>The receiving node is not the attestation authority for facts it relays. Re-attesting would silently alter provenance.</dd>
</div>

<div>
<dt>Garden slug must be unique per node</dt>
<dt><span className="stigmem-fields__type">URI hygiene</span></dt>
<dd>Gardens are addressed by <code>stigmem://authority/garden/{`{slug}`}</code>; collisions on slug would make the URI non-unique.</dd>
</div>

</div>

<details>
<summary>Revisions before v1.0: the pre-reset spec-draft</summary>

**From `stigmem-spec-the pre-reset spec-draft.md`:**

| Decision | Rationale |
|---|---|
| Immutable facts | Preserves audit trail; contradictions first-class |
| JSON/HTTP for v0.1 | Universal; binary encoding is the pre-reset design work |
| Auth pre-reset via API key | Simplest credential that enforces identity; JWTs/DIDs in the pre-reset design work |
| Retraction as assertion | Preserves audit trail; avoids mutation complexity |
| No `PATCH /v1/facts/:id` | Would imply mutation, breaking immutability invariant |
| Scope as enum | ACLs add complexity before federation exists |
| Confidence as float | More expressive than boolean; maps to LLM output probability |
| No global decay standard | Operators have heterogeneous retention needs |
| Handoff via fact refs | Keeps fabric as source of truth |
| Intent envelope separate | Facts = world state; intents = desired transitions |
| `text` type | Multi-paragraph bodies don't fit `string` |
| `text` size cap (64 KB) | Prevents unbounded memory growth; ref pattern covers larger blobs |
| Reification via `stigmem:rel:` | RDF-proven pattern for N-ary relationships |
| `valid_until` field | Separates temporal scope from confidence |
| `/.well-known/stigmem` endpoint | Enables auth-mode detection and peer discovery |
| Auth stub in pre-reset → impl pre-reset | pre-reset delivery validated model against real data |
| `node_url` in well-known | Required for federation peer-discovery; also useful for client config |
| `GET /v1/facts/:id` | Needed in practice: dogfood client needed point-lookup for readback |
| Ed25519 for peer tokens | Fast, compact, widely supported; avoids RSA key size debates |
| HLC over pure vector clocks | HLC is O(1) state per node; vector clocks are O(N) and impractical beyond small clusters |
| Pull-based replication default | Simpler operational model; push is opt-in for latency-sensitive deployments |
| Contradiction as first-class fact | Forces explicit reconciliation; prevents silent data corruption across nodes |
| Peer tokens separate from API keys | Federation auth is machine-to-machine with short TTL; API keys are long-lived operator credentials |
| Nonce window 5 minutes | Balances replay protection with clock skew tolerance; tunable via env var |
| Conflict entities not federated | Conflicts are local accounting; federating them would cause infinite loops |
| Per-scope key restrictions additive | Default-all with opt-out is more backward-compatible; default-none would break existing deployments |
| Formal entity URI scheme in pre-reset | Informal `user:alice` URIs are ambiguous under federation — two peers can have different `user:alice`. Formal `stigmem://authority/type/id` binds identity to the node that owns the namespace. Deprecation-warning approach preserves backward compat while driving migration. |
| Capability negotiation required in pre-reset | the pre-reset line shipped two adapters with distinct relation namespaces. Without capability exchange, federated peers silently replicate relations they cannot interpret. Required negotiation prevents contradiction storms on semantically-opaque relations. |
| Crash-forbidden adapter contract | Adapters are middleware in existing agent processes; a Stigmem node failure must not take down the agent. Crash-forbidden is an explicit ABI invariant so all adapter authors share the same degradation model. |
| Case normalization at ingest (pre-reset) | `project/EG-18` and `project/eg-18` created silent entity fragments — the root cause in earlier work. Normalizing at ingest (not query) keeps query O(1) on indexed lookups and prevents non-canonical data from accumulating in the store. Informal URIs are lowercased in place (not converted to formal) to preserve the §2.5 anti-rewrite invariant. |
| Lint as first-class operation (pre-reset) | Karpathy LLM-Wiki analysis (during the pre-reset design work) identified that adapter-side ad-hoc contradiction/stale queries are inconsistent and fragile. A single normative `POST /v1/lint` provides uniform sweep semantics with deterministic severity levels, enabling the decay engine (pre-reset) to delegate sweep discovery to the node rather than each adapter reimplementing it. |
| Lint uses POST, not GET (pre-reset) | The lint request body can include multiple optional filter fields (`entity`, `relation`, `checks`, `stale_lookahead_s`). A GET query string with complex filters risks URL-length limits and encoding ambiguity. POST body is unambiguous. Lint is idempotent despite using POST; this is documented explicitly (§14.5). |
| Lint is strictly read-only (pre-reset) | Diagnostic operations must not modify state. A lint sweep that auto-retracted stale facts would conflate discovery with action, removing the human/agent approval step before retraction. Lint observes; retraction is a deliberate subsequent operation. |
| Four lint checks, independently selectable (pre-reset) | Contradiction detection is an operational concern (run continuously); stale/orphan sweeps are maintenance tasks (run on schedule); broken-ref detection is a data-quality check (run during ingestion audits). Decoupling them lets callers compose the sweep they need without paying for all four. |
| Decay sweeper separate from lint (pre-reset) | Lint is read-only diagnosis; decay is write-path remediation (confidence reduction + retraction). Merging them would violate the lint read-only invariant and make audit harder. Sweeper runs are logged separately from lint runs. |
| confidence decay over `valid_until` reduction (pre-reset) | Setting `valid_until` is a binary expiry; confidence decay is gradual. For knowledge that degrades over time (e.g. an agent's working context facts), a smooth confidence reduction gives downstream agents a calibrated signal to de-weight the fact before it disappears entirely. Both mechanisms coexist. |
| Company-scoped re-federation blocked by default (pre-reset) | the pre-reset spec 4-node topology revealed that a relay node with wider permissions than the originating peer could silently propagate company-internal facts to third parties. Blocking re-federation by default closes this scope escalation path while preserving the explicit opt-in escape hatch for operators who need it. |
| Relay lag signal in response headers (pre-reset) | Subscribers cannot know a relay's inbound lag from the facts themselves (HLC timestamps reflect write time, not ingestion lag). A response header is the lowest-overhead signaling path; it does not require a new route and is backward-compatible (old clients ignore unknown headers). |

</details>
