# Upstream Validation Evidence

This file tracks the public closeout evidence for the 2026-05-06 upstream
validation overlay, evaluated against `main` commit
`893fe82057355f57419f6a0cd262f49d3677db41`.

The Internal-Comms source index remains
`stigmem/analyses/upstream-findings-evaluation.md`. This public-repo note records
only the issue and PR evidence needed to keep GitHub planning coherent.

| Order | Requirement | Issue | Closing evidence |
| --- | --- | --- | --- |
| 1 | OpenClaw evidence/status capture | [#159](https://github.com/eidetic-labs/stigmem/issues/159) | Closed by [PR #167](https://github.com/eidetic-labs/stigmem/pull/167); follow-up ClawHub/OpenClaw alpha framing refresh tracked by [#169](https://github.com/eidetic-labs/stigmem/issues/169) and closed by [PR #177](https://github.com/eidetic-labs/stigmem/pull/177). |
| 2 | Version/license alignment follow-up | [#160](https://github.com/eidetic-labs/stigmem/issues/160) | Closed by [PR #175](https://github.com/eidetic-labs/stigmem/pull/175); runtime/prose version emitter drift coverage extended by [#168](https://github.com/eidetic-labs/stigmem/issues/168) / [PR #176](https://github.com/eidetic-labs/stigmem/pull/176). |
| 3 | Security-doc alignment and evidence registry | [#161](https://github.com/eidetic-labs/stigmem/issues/161) | Closed by [PR #170](https://github.com/eidetic-labs/stigmem/pull/170). |
| 4 | HLC bounds | [#162](https://github.com/eidetic-labs/stigmem/issues/162) | Closed by [PR #171](https://github.com/eidetic-labs/stigmem/pull/171). |
| 5 | API-key hashing / Argon2id migration | [#163](https://github.com/eidetic-labs/stigmem/issues/163) | Closed by [PR #172](https://github.com/eidetic-labs/stigmem/pull/172). |
| 6 | Missing risk entries / risk register cleanup | [#164](https://github.com/eidetic-labs/stigmem/issues/164) | Closed by [PR #174](https://github.com/eidetic-labs/stigmem/pull/174). |
| 7 | Repo/doc structure follow-up | [#165](https://github.com/eidetic-labs/stigmem/issues/165) | Closed by [PR #181](https://github.com/eidetic-labs/stigmem/pull/181); decomposition follow-up tracked by [#178](https://github.com/eidetic-labs/stigmem/issues/178), [#179](https://github.com/eidetic-labs/stigmem/issues/179), and [#180](https://github.com/eidetic-labs/stigmem/issues/180). |
| 8 | AI disclosure follow-up | [#166](https://github.com/eidetic-labs/stigmem/issues/166) | Closed by [PR #182](https://github.com/eidetic-labs/stigmem/pull/182). |

## Tracker Closeout

Issue [#158](https://github.com/eidetic-labs/stigmem/issues/158) is complete
when this evidence table and the corresponding Internal-Comms checklist update
land. The remediation order is preserved, all child issues link back to the
upstream evaluation, and no active hardened-core plan depends on the outdated broad
claim that current `main` lacks all Phase 12-era controls.
