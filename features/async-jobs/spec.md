# Async Jobs Spec

## Scope

Async jobs define the shared node behavior used when a long-running operation is
accepted for background execution instead of completing synchronously in the
initial HTTP request.

This feature currently covers:

- lint sweeps that return `202 Accepted` from `POST /v1/lint`;
- decay sweeps that return `202 Accepted` from `POST /v1/decay/sweep`;
- polling endpoints for lint and decay job ids;
- terminal job result stability;
- isolation between job types.

This feature does not own lint finding semantics, decay policy semantics, or
the broader lifecycle semantics of facts. Those remain owned by the lint and
decay records.

## Execution Contract

Operations that support async execution evaluate the request scope against the
configured threshold. The reference node uses `STIGMEM_ASYNC_JOB_THRESHOLD`,
defaulting to `100000` facts.

Small scopes should complete synchronously and return the operation-specific
HTTP 200 response. Large scopes may return HTTP 202 with:

| Field | Meaning |
| --- | --- |
| `job_id` | Identifier for the accepted background job. |
| `status` | Initial status, normally `pending`. |
| `estimated_s` | Advisory estimate in seconds. |

Dry-run decay sweeps always use the synchronous path because they do not write
new facts.

## Polling Contract

Callers poll the operation-specific job endpoint:

```http
GET /v1/lint/jobs/{job_id}
GET /v1/decay/jobs/{job_id}
```

Known jobs eventually return either a completed result or a terminal failure.
Unknown job ids return 404. A job id created for one operation type must not be
visible through another operation type's polling endpoint.

## Lifecycle

```text
pending -> running -> done
                  -> error
```

Terminal states are stable. Repeated polling of a completed job returns the same
result payload.

## Canonical Spec Assignment

There is no Spec-X assignment for async jobs. The current behavior is specified
through the lint and decay surfaces that use the shared job implementation, but
the shared job lifecycle does not own a standalone protocol identifier.
