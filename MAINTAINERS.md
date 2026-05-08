# Maintainers

This file is the canonical record of who currently holds maintenance roles in the stigmem project. It is updated as the team evolves.

This file lives in the stigmem repo root. ADRs reference roles ("the founder," "the founding team," "contributors"); this file maps those roles to current GitHub identities.

---

## Founder

- **[@offbyonce](https://github.com/offbyonce)** — Founder, Eidetic Labs.

## Founding team

Additional team members listed upon their consent.

## Other contributors

Contributions from anyone outside the listed roles above are recorded in git history and welcome under [`CONTRIBUTING.md`](CONTRIBUTING.md). Inclusion in this file is a separate, opt-in step.

---

## Authority and approval

Per [ADR-001 § *Contributor approval rule*](docs/adr/001-versioning.md), sign-off on ADRs, ADR amendments, and PRs through Phase B requires **either** two contributors **or** the founder alone. The founder takes responsibility for the validation discipline whenever signing alone — the guardrail against AI-velocity-outrunning-validation (per the v1.0 retraction narrative) lives with the founder when they approve solo.

Audit logs (plugin registration per ADR-011, PR approval records, ADR sign-off commits) show the actual signing identities. This file describes who currently holds the roles; git history is the durable record of who exercised them.

---

## Plugin signing identities (per ADR-011)

When the C1 plugin architecture (ADR-011) ships its production signing infrastructure, **Eidetic Labs** is the default trusted publisher for stigmem core plugins (the seven cross-cutting feature plugins shipped in Phase A). Operators may add additional trusted publishers in their own deployments.

The Sigstore identity mapping for Eidetic Labs is documented separately in `docs/Operate/Plugins/signing.md` (per ADR-005 IA, lands in Phase A docs work).

---

## Updating this file

- **Adding an entry:** the person being added must explicitly consent in writing (via PR comment, email, or other auditable channel). The PR must reference the consent.
- **Modifying an entry:** the entry's holder approves the change.
- **Removing an entry (voluntary):** the entry's holder may remove themselves at any time without further approval.
- **Removing an entry (involuntary):** treat as a governance change requiring an ADR amendment.

---

*Last updated: 2026-05-07. Updated per [ADR-001 § *Contributor approval rule*](docs/adr/001-versioning.md).*
