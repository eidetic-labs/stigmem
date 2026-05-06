---
title: §9. Namespace Registry
sidebar_label: §9 Namespace Registry
audience: Spec
description: "Stigmem spec section 9 — Reserved relation prefixes (memory, system, stigmem, garden) and community registry process."
---

# §9. Namespace Registry {#section-9}

**Status:** Stable

Reserved relation prefixes (memory, system, stigmem, garden) and community registry process.

**Authoritative source:** [`spec/stigmem-spec-v1.0.md`](https://github.com/Eidetic-Labs/stigmem/blob/main/spec/stigmem-spec-v1.0.md)

:::note Section body
Each subsection below shows the most recent normative text from the spec source. When earlier spec drafts also contained text for the same subsection, those revisions are collapsed under a `Revisions` accordion beneath it — open one to see what changed. Subsections that only appear in one draft render as plain text with no accordion.
:::

### §9.1 Reserved prefixes (v0.9 additions) {#section-9-1}

*Existing entries from v0.8 unchanged.*

| Prefix | Governed by | Purpose |
|---|---|---|
| `garden:` | Spec maintainers | Garden metadata facts: `garden:member`, `garden:role`, `garden:scope` |
| `stigmem:attest:` | Spec maintainers | Reserved for future per-entity attestation-policy facts (e.g. required-source assertions on a scope or garden). v0.9 source attestation is a pure API operation; this prefix is reserved to prevent squatting ahead of fact-based attestation policy extensions. |

<details>
<summary>Revisions before v1.0: v0.8-draft</summary>

**From `stigmem-spec-v0.8-draft.md`:**

### 9.1 Reserved prefixes (maintained by spec)

| Prefix | Governed by | Purpose |
|---|---|---|
| `stigmem:` | Spec maintainers | Core protocol relations: `stigmem:ttl`, `stigmem:received_from`, `stigmem:member`, `stigmem:conflict:between`, `stigmem:conflict:status`, `stigmem:resolves` |
| `rel:` | Spec maintainers | Reification primitives: `rel:subject`, `rel:object`, `rel:type` |
| `stigmem:lint:` | Spec maintainers | Reserved for future lint-related protocol relations. v0.7 lint is a pure API operation (no fact assertions); this prefix is reserved to prevent squatting ahead of Phase 6 lint enhancements. |
| `stigmem:decay:` | Spec maintainers | Reserved for decay sweeper protocol relations. v0.8 decay sweep is a pure API operation; this prefix is reserved for future decay policy fact assertions (e.g. per-entity decay overrides). |

</details>

### §9.2 Community-registered prefixes (v0.9 additions) {#section-9-2}

*(No new community prefixes in v0.9.)*

---

<details>
<summary>Revisions before v1.0: v0.8-draft</summary>

**From `stigmem-spec-v0.8-draft.md`:**

### 9.2 Community-registered prefixes

| Prefix | Status | Notes |
|---|---|---|
| `memory:` | Registered | Agent memory: role, preference, context |
| `intent:` | Registered | Intent envelope machine-readable facts; includes `intent:handoff_to`, `intent:handoff_summary`, `intent:context_ref`, `intent:continuation`, `intent:escalation`, `intent:escalate_to`, `intent:goal` |
| `roadmap:` | Registered | Project/product state facts; includes `roadmap:decision`, `roadmap:constraint`, `roadmap:status`, `roadmap:summary` |
| `preference:` | Registered | User/agent preferences |
| `paperclip:` | Registered (Phase 4) | Paperclip adapter lifecycle facts: `paperclip:checkout`, `paperclip:issue_status`, `paperclip:last_active`, `paperclip:blocked_by` |

</details>

### §9.3 Experimental prefix {#section-9-3}

`x-` prefix is reserved for informal/experimental use. No registration required.

---
