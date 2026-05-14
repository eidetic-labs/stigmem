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

## 1. Extraction Status

This component spec extracts the lint semantics that previously lived in the
monolithic `stigmem-spec-v0.9.0a1.md` lineage. It defines the read-only lint
sweep contract, finding shape, severity mapping, filters, and async job
behavior for stigmem v0.9.0aN.

The HTTP route shape remains owned by `Spec-03-HTTP-API`. This spec owns what a
lint request means and how findings are interpreted.

## 2. Purpose

Lint is a first-class diagnostic sweep over facts in one scope. A lint run MUST
be read-only: it MUST NOT assert facts, retract facts, resolve conflicts, create
or delete entities, or mutate storage state other than implementation-local job
bookkeeping for asynchronous execution.

Lint results are advisory. Operators, agents, and tools MAY use findings to
drive remediation workflows, but remediation is outside this spec.

## 3. Checks

Nodes MUST support these check names:

| Check | Meaning |
|---|---|
| `contradiction` | Report unresolved contradictions among live facts. |
| `stale` | Report live facts that are expired or will expire within the requested lookahead window. |
| `orphan` | Report entities that have no live facts remaining in the requested scope. |
| `broken_ref` | Report live reference-valued facts whose target entity has no live facts in the requested scope. |
| `namespacing` | Report live facts whose relation does not use a namespaced relation prefix. |

If a lint request omits `checks` or supplies an empty list, the node MUST run
all supported checks.

## 4. Scope And Filters

Every lint run is confined to exactly one requested scope. Implementations MUST
apply the caller's read authorization for that scope before inspecting facts.

Lint requests MAY include:

| Field | Meaning |
|---|---|
| `scope` | Required scope to inspect. |
| `checks` | Optional list of check names. Empty or omitted means all checks. |
| `entity` | Optional entity URI filter. |
| `relation` | Optional relation filter. |
| `stale_lookahead_s` | Optional non-negative stale lookahead window, in seconds. |

Unknown scopes or check names MUST fail validation. A caller without read access
to the requested scope MUST receive an authorization failure.

## 5. Finding Shape

Each lint finding MUST include:

| Field | Meaning |
|---|---|
| `check` | Check name that produced the finding. |
| `severity` | One of `error`, `warning`, or `info`. |
| `entity` | Entity URI most directly associated with the finding. |
| `relation` | Relation associated with the finding, or null if not applicable. |
| `fact_ids` | Fact ids relevant to the finding. |
| `detail` | Human-readable explanation suitable for logs and operator output. |

Findings SHOULD be deterministic for a stable input store so repeated lint runs
are useful in tests and operator diffs.

## 6. Severity Mapping

Nodes MUST use this baseline severity mapping:

| Check condition | Severity |
|---|---|
| Unresolved contradiction | `error` |
| Already-expired fact | `warning` |
| Fact expiring within `stale_lookahead_s` | `info` |
| Orphaned entity | `info` |
| Broken reference | `warning` |
| Broken reference for `intent:handoff_to` or `intent:context_ref` | `error` |
| Relation without a namespace prefix | `warning` |

Implementations MAY add implementation-specific detail text, but they MUST NOT
downgrade the severities above.

## 7. Result Shape

A completed lint run MUST return:

| Field | Meaning |
|---|---|
| `findings` | List of lint findings. |
| `checked_at` | Timestamp when the run completed. |
| `scope` | Scope inspected. |
| `checks_run` | Checks that were executed. |
| `fact_count` | Number of facts considered before check-specific filtering. |

## 8. HTTP And Async Execution

The stable HTTP lint surface includes:

```http
POST /v1/lint
GET /v1/lint/jobs/{job_id}
```

Small lint runs SHOULD complete synchronously with a completed result body.
Large lint runs MAY return `202 Accepted` with:

| Field | Meaning |
|---|---|
| `job_id` | Identifier for the asynchronous lint job. |
| `status` | Initial job status, normally `pending`. |
| `estimated_s` | Advisory estimated completion time in seconds. |

The reference node uses the configured `async_job_threshold` to choose the async
path; its default threshold is 100,000 facts. Other conforming nodes MAY choose
a different documented threshold.

Polling `GET /v1/lint/jobs/{job_id}` MUST eventually return either the completed
lint result or a terminal failure status for known jobs. Unknown job ids MUST be
reported as not found.

## 9. MCP And Tooling

MCP wrappers and local operator tools that expose lint MUST preserve this spec's
scope, check, filter, and finding semantics. Tooling MAY present findings in a
more ergonomic format, but MUST NOT hide `error` severity findings by default.

## 10. Out Of Scope

This spec does not define:

- conflict resolution or fact retraction workflows;
- decay, synthesis, or confidence-repair behavior;
- adapter-specific context repair;
- storage query plans or indexing strategy;
- plugin health checks;
- the backing implementation of asynchronous job queues.
