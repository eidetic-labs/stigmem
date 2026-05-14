---
spec_id: Spec-03-HTTP-API
version: 0.1.0-alpha.0
status: Draft
applies_to: stigmem v0.9.0aN
last_updated: 2026-05-14
supersedes: spec/stigmem-spec-v0.9.0a1.md section 5 API surface material
depends_on:
  - Spec-01-Core >= 0.1.0-alpha.0
  - Spec-02-Scopes-and-ACL >= 0.1.0-alpha.0
---

# Spec-03-HTTP-API

HTTP API contract for fact CRUD, query, conflict management, federation endpoints, garden endpoints, lint, and synthesis routing that remain in the current reference node surface.

## Extraction Status

This is the ADR-010 metadata stub for the modular spec migration. The normative text remains in [`../stigmem-spec-v0.9.0a1.md`](../stigmem-spec-v0.9.0a1.md) and the rendered API docs until the section-by-section extraction PR migrates the prose into this file.

## Legacy Sections

- §5 Wire Format
- §5.1 through §5.25 endpoint descriptions, split by feature ownership as extraction proceeds
