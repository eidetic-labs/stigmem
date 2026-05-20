---
spec_id: Spec-20-Lint-Semantics
version: 0.1.0-alpha.0
status: Draft
audience: Spec
applies_to: stigmem v0.9.0aN
last_updated: 2026-05-14
supersedes: spec/stigmem-spec-v0.9.0a1.md section 14 lint-semantics material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-02-Scopes-and-ACL >= 0.1.0-alpha.0
  - Spec-03-HTTP-API >= 0.1.0-alpha.0
  - Spec-15-Fact-Semantics >= 0.1.0-alpha.0
  - Spec-16-Namespace-Registry >= 0.1.0-alpha.0
---

# Spec-20-Lint-Semantics

<p className="stigmem-meta"><span>4 min read</span><span>Spec contributor · SDK author</span><span>Draft · v0.9.0aN</span></p>

<div className="stigmem-lead">

**What this spec defines**

The read-only lint sweep contract, finding shape, severity mapping,
filters, and async job behavior. HTTP route shape is owned by
`Spec-03-HTTP-API`; this spec owns what a lint request means and
how findings are interpreted.

</div>

## Extraction status

This component spec extracts the lint semantics that previously
lived in the monolithic `stigmem-spec-v0.9.0a1.md` lineage.

## Purpose

<div className="stigmem-keypoint">

**Lint is a read-only diagnostic sweep over facts in one scope.**

A lint run MUST NOT assert facts, retract facts, resolve conflicts,
create or delete entities, or mutate storage state other than
implementation-local job bookkeeping for asynchronous execution.
Lint results are advisory.

</div>

## Checks

Nodes MUST support these check names:

<div className="stigmem-fields">

<div>
<dt>Check</dt>
<dt><span className="stigmem-fields__type">Target</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>contradiction</code></dt>
<dt><span className="stigmem-fields__type">live facts</span></dt>
<dd>Report unresolved contradictions among live facts.</dd>
</div>

<div>
<dt><code>stale</code></dt>
<dt><span className="stigmem-fields__type">expiry</span></dt>
<dd>Report live facts that are expired or will expire within the requested lookahead window.</dd>
</div>

<div>
<dt><code>orphan</code></dt>
<dt><span className="stigmem-fields__type">entities</span></dt>
<dd>Report entities that have no live facts remaining in the requested scope.</dd>
</div>

<div>
<dt><code>broken_ref</code></dt>
<dt><span className="stigmem-fields__type">references</span></dt>
<dd>Report live reference-valued facts whose target entity has no live facts in the requested scope.</dd>
</div>

<div>
<dt><code>namespacing</code></dt>
<dt><span className="stigmem-fields__type">relations</span></dt>
<dd>Report live facts whose relation does not use a namespaced relation prefix.</dd>
</div>

</div>

If a lint request omits `checks` or supplies an empty list, the node
MUST run all supported checks.

## Scope and filters

Every lint run is confined to exactly one requested scope.
Implementations MUST apply the caller's read authorization for that
scope before inspecting facts.

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Optionality</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">required</span></dt>
<dd>Required scope to inspect.</dd>
</div>

<div>
<dt><code>checks</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>List of check names. Empty or omitted means all checks.</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Entity URI filter.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Relation filter.</dd>
</div>

<div>
<dt><code>stale_lookahead_s</code></dt>
<dt><span className="stigmem-fields__type">optional</span></dt>
<dd>Non-negative stale lookahead window, in seconds.</dd>
</div>

</div>

Unknown scopes or check names MUST fail validation. A caller without
read access to the requested scope MUST receive an authorization
failure.

## Finding shape

Each lint finding MUST include:

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>check</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Check name that produced the finding.</dd>
</div>

<div>
<dt><code>severity</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>One of <code>error</code>, <code>warning</code>, or <code>info</code>.</dd>
</div>

<div>
<dt><code>entity</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Entity URI most directly associated with the finding.</dd>
</div>

<div>
<dt><code>relation</code></dt>
<dt><span className="stigmem-fields__type">nullable</span></dt>
<dd>Relation associated with the finding, or null if not applicable.</dd>
</div>

<div>
<dt><code>fact_ids</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Fact ids relevant to the finding.</dd>
</div>

<div>
<dt><code>detail</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Human-readable explanation suitable for logs and operator output.</dd>
</div>

</div>

Findings SHOULD be deterministic for a stable input store so
repeated lint runs are useful in tests and operator diffs.

## Severity mapping

Nodes MUST use this baseline severity mapping:

<div className="stigmem-fields">

<div>
<dt>Condition</dt>
<dt><span className="stigmem-fields__type">Severity</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Unresolved contradiction</dt>
<dt><span className="stigmem-fields__type">error</span></dt>
<dd>Highest priority finding.</dd>
</div>

<div>
<dt>Already-expired fact</dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Expiring within <code>stale_lookahead_s</code></dt>
<dt><span className="stigmem-fields__type">info</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Orphaned entity</dt>
<dt><span className="stigmem-fields__type">info</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Broken reference</dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>—</dd>
</div>

<div>
<dt>Broken <code>intent:handoff_to</code>/<code>intent:context_ref</code></dt>
<dt><span className="stigmem-fields__type">error</span></dt>
<dd>Promoted because handoff routing depends on these refs.</dd>
</div>

<div>
<dt>Relation without namespace prefix</dt>
<dt><span className="stigmem-fields__type">warning</span></dt>
<dd>—</dd>
</div>

</div>

<div className="stigmem-keypoint">

**Implementations MAY add detail text, but MUST NOT downgrade the severities above.**

</div>

## Result shape

A completed lint run MUST return:

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Required</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>findings</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>List of lint findings.</dd>
</div>

<div>
<dt><code>checked_at</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Timestamp when the run completed.</dd>
</div>

<div>
<dt><code>scope</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Scope inspected.</dd>
</div>

<div>
<dt><code>checks_run</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Checks that were executed.</dd>
</div>

<div>
<dt><code>fact_count</code></dt>
<dt><span className="stigmem-fields__type">yes</span></dt>
<dd>Number of facts considered before check-specific filtering.</dd>
</div>

</div>

## HTTP and async execution

The stable HTTP lint surface includes:

```http
POST /v1/lint
GET /v1/lint/jobs/{job_id}
```

Small lint runs SHOULD complete synchronously with a completed
result body. Large lint runs MAY return `202 Accepted` with:

<div className="stigmem-fields">

<div>
<dt>Field</dt>
<dt><span className="stigmem-fields__type">Type</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>job_id</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Identifier for the asynchronous lint job.</dd>
</div>

<div>
<dt><code>status</code></dt>
<dt><span className="stigmem-fields__type">string</span></dt>
<dd>Initial job status, normally <code>pending</code>.</dd>
</div>

<div>
<dt><code>estimated_s</code></dt>
<dt><span className="stigmem-fields__type">number</span></dt>
<dd>Advisory estimated completion time in seconds.</dd>
</div>

</div>

The reference node uses the configured `async_job_threshold` to
choose the async path; its default threshold is 100,000 facts. Other
conforming nodes MAY choose a different documented threshold.

Polling `GET /v1/lint/jobs/{job_id}` MUST eventually return either
the completed lint result or a terminal failure status for known
jobs. Unknown job ids MUST be reported as not found.

## MCP and tooling

<div className="stigmem-keypoint">

**MCP wrappers and operator tools MUST preserve this spec's scope, check, filter, and finding semantics.**

Tooling MAY present findings in a more ergonomic format, but MUST
NOT hide `error` severity findings by default.

</div>

## Out of scope

This spec does not define:

<div className="stigmem-grid">

<div><h4>Conflict resolution</h4><p>Or fact retraction workflows.</p></div>
<div><h4>Decay/synthesis/confidence-repair</h4></div>
<div><h4>Adapter-specific context repair</h4></div>
<div><h4>Storage query plans</h4><p>Or indexing strategy.</p></div>
<div><h4>Plugin health checks</h4></div>
<div><h4>Async job queue implementation</h4></div>

</div>
