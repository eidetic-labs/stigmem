---
id: async-jobs
title: Async Lint / Decay Jobs
sidebar_label: Async Jobs
---

# Async Lint / Decay Jobs

**Audience:** Node operators and API consumers managing fact quality at scale.  
**Spec reference:** §14.5 (lint), §15.4 (decay)  
**Track:** F3 — [ACM-103](/ACM/issues/ACM-103) (pre-GA hardening)

## Overview

For small scopes, lint and decay routes respond synchronously (HTTP 200). When a
scope exceeds the `async_job_threshold` (default: 100 000 facts), the node returns
HTTP 202 and runs the sweep in the background. Dry-run mode always responds
synchronously regardless of scope size.

## Starting a sweep

```bash
# Lint sweep — sync (scope < threshold) or async (scope > threshold)
curl -X POST http://localhost:8000/v1/lint \
  -H 'X-API-Key: <key>' \
  -H 'Content-Type: application/json' \
  -d '{"scope": "company"}'

# Synchronous response (small scope)
# HTTP 200 — { "issues": [...], "checked": 42 }

# Asynchronous response (large scope)
# HTTP 202 — { "job_id": "8a3f...c1", "status": "pending" }
```

```bash
# Decay sweep (same pattern)
curl -X POST http://localhost:8000/v1/decay \
  -H 'X-API-Key: <key>' \
  -H 'Content-Type: application/json' \
  -d '{"scope": "company"}'
```

## Polling a job

```bash
# Poll lint job status
curl http://localhost:8000/v1/lint/jobs/<job_id> \
  -H 'X-API-Key: <key>'

# Response while running
{ "job_id": "8a3f...c1", "status": "running" }

# Response when complete
{ "job_id": "8a3f...c1", "status": "done", "result": { "issues": [...], "checked": 150042 } }

# Response on error
{ "job_id": "8a3f...c1", "status": "error", "error": "scope not found" }
```

```bash
# Poll decay job status (same shape)
curl http://localhost:8000/v1/decay/jobs/<job_id> \
  -H 'X-API-Key: <key>'
```

## Job lifecycle

```
pending  →  running  →  done
                     ↘  error
```

Job state is stable once `done` or `error` — multiple GET polls return the same result.

## Key invariants (spec §14.5, §15.4)

- **Dry-run bypass:** `mode=dry_run` always takes the synchronous 200 path.
- **Cross-type isolation:** a lint `job_id` returns 404 via the decay job endpoint, and vice versa.
- **Scope-local threshold:** the async threshold is evaluated per-scope, not globally.
- **Idempotent result:** completed job results are stable — polling returns the same response every time.

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `STIGMEM_ASYNC_JOB_THRESHOLD` | `100000` | Facts-per-scope threshold above which sweeps run asynchronously |

## See also

- [Decay semantics](./decay) — `DecayPolicy` configuration and confidence reduction
- [Querying facts](./querying-facts) — filter by confidence after a decay sweep
