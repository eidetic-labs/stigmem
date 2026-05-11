# Audit triage registry

**Status:** Current. Maintained per the open security-state policy.
**Scope:** Alerts raised by static-analysis tools (CodeQL, bandit, pip-audit, pnpm audit, …) that have been classified as false positives or knowingly suppressed. The registry persists the **rationale** for each classification in tracked source so it survives outside the GitHub UI (alert comments are not in-repo and can be lost on fork or re-import).

This file complements:

- [`SECURITY.md`](../../SECURITY.md) § Security Posture — operator-facing summary and per-PR triage groups.
- [`threat-model.md`](threat-model.md) — risk register (R-XX entries). Only **real** risks land there; this file records **non-risks**.
- [ADR-018](../../docs/adr/018-security-documentation-colocation.md) — establishes the colocation principle that justifies an in-repo registry over GitHub-UI-only dismissal comments.

## How to use this file

Every triage decision against an open security alert that ends in **dismiss as false positive** or **suppress with rationale** SHOULD add an entry here, including:

1. The alert number(s) and rule id.
2. The location at the time of triage.
3. The root cause (why the tool flagged it).
4. The reason the flag is not a vulnerability.
5. The remediation taken (structural fix, regex tightening, accepted suppression, …) and the PR that landed it.

Entries are append-only. If a previously-dismissed alert is later determined to be a real bug, add a new entry under the same date acknowledging the revision and link to the fix; do **not** edit the historical entry.

---

## CodeQL

### 2026-05-11 — conditional SQL-fragment assembly (7 SQL + 1 transitive ReDoS)

**Alerts:** [#18](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/18), [#19](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/19), [#21](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/21), [#22](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/22), [#23](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/23), [#24](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/24), [#25](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/25), [#26](https://github.com/Eidetic-Labs/stigmem/security/code-scanning/26).

**Rules:** 7× `py/sql-injection`, 1× `py/polynomial-redos`.

**Locations at triage time:**

- `node/src/stigmem_node/routes/lint.py` lines 94, 124, 185, 220, 254 (5 builders).
- `node/src/stigmem_node/routes/facts.py` line 246.
- `node/src/stigmem_node/routes/synthesize.py` line 105.
- `node/src/stigmem_node/storage/postgres_backend.py` line 146 (transitive taint from the SQL builders into `_STRFTIME_EPOCH_RE.sub()`).

**Root cause:** CodeQL's taint analyzer cannot reason about Python's conditional-string-fragment assembly pattern:

```python
conditions = ["f.tenant_id = ?"]
params = [tenant_id]
if entity:
    conditions.append("f.entity = ?")  # ← literal SQL fragment
    params.append(entity)              # ← user value (parameter-bound)
sql = f"SELECT * FROM facts WHERE {' AND '.join(conditions)}"
conn.execute(sql, params)
```

The user value (`entity`) reaches an f-string control flow because the branch that appends it is conditional on the value. CodeQL marks `sql` as user-tainted at the `execute` sink, even though only a string-literal SQL fragment was interpolated and the user value was bound as a parameter. For the ReDoS alert (#21), the same tainted `sql` flows one hop further into `_pg_translate`'s `_STRFTIME_EPOCH_RE.sub(...)`, where the analyzer flags the regex as a polynomial-ReDoS sink — even though in practice the regex only sees the SQL skeleton text (a string literal at every call site).

**Why these are not vulnerabilities:** every user-supplied value reaches the database as a bound parameter via `?` placeholders. The SQL **text** that CodeQL sees concatenated never contains user input — only literal strings the developer wrote. The regex in `_pg_translate` only processes those same literal SQL strings, plus migration files that ship in the repository (developer-authored, trusted at the supply-chain boundary). There is no flow from a network input to a SQL parser or a regex engine that an attacker could exploit.

**Why suppression was not the right fix:** `# nosec` comments satisfy bandit but **CodeQL does not honor them**. Confirmed in two prior triages:

- PR #106 — `py/clear-text-logging-sensitive-data`: inline suppression attempts failed; resolved by design pivot to a user-provides-key flow.
- PR #112 follow-up — these same SQL injection alerts: this triage.

Both produced the same conclusion: the durable remediation is structural, not declarative.

**Remediation:** [PR #117](https://github.com/Eidetic-Labs/stigmem/pull/117) refactors all three SQL builders to a constant-SQL pattern. The WHERE clause becomes a module-level string constant and optional filters are gated by bound parameters using `(? IS NULL OR col = ?)` (or a `? = 1` sentinel for boolean toggles). After the refactor:

- No f-string concatenation reachable from user input.
- No taint flow from `routes/` to `_pg_translate`'s regex.
- 7 `# nosec B608` comments removed (no longer needed).
- Belt-and-suspenders: bounded quantifiers on `_STRFTIME_EPOCH_RE` (`\s{0,16}`, `[^)]{1,256}?`) in case the transitive-taint break alone is not enough to close #21.

**Status:** Closed on PR #117 + PR #121 merge (CodeQL re-scan).

**Follow-up — 2026-05-11, issue #121:** CodeQL re-scanned `main` after PR #117 merged and re-opened alerts #22 (`facts.py:263`) and #26 (`synthesize.py:110`). Both moved one line — from the f-string concatenation site that PR #117 removed, to the `conn.execute(sql, params)` call site. Diagnosis: even though the SQL string is now a module-level constant, the builder function (`_build_as_of_query`, `_build_synthesize_sql`) still **returned** the SQL string from a function whose arguments are user-controlled. CodeQL's interprocedural taint engine follows the user input into the function and out via the tuple return, tagging the returned SQL as tainted even though its value is invariant.

Resolution (PR #121): split each builder so the module-level SQL constant is referenced **directly at the call site** and the builder returns **only** the params list (`_build_as_of_params`, `_build_synthesize_params`). This breaks the user-input → tuple-return → SQL data-flow path. No change to the SQL text itself.

Lesson: even after the constant-SQL refactor, the SQL string must never appear in the return type of a function that accepts user input. The taint-precision gap is wider than the f-string-only case originally diagnosed.

**No threat-model entries added:** the exploitation conditions do not exist; recording the alerts in `threat-model.md` would mislead future readers into treating them as real residual risks. The Rev 2.2 entry in `threat-model.md` § 10 documents the triage decision without claiming a new residual risk.

---

## bandit, pip-audit, pnpm audit

No long-form entries yet. Bandit suppressions are inline (`# nosec BXXX`) and explained at the call site; per-alert dependency suppressions are documented in `SECURITY.md` Groups A and B. If a bandit or dependency-audit suppression ever requires more than one line of rationale, prefer adding an entry to this file over expanding the inline comment.
