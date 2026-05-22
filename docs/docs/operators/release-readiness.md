---
title: Release Readiness
sidebar_label: Release Readiness
description: Per-release entry and exit criteria, scope, and current status for active Stigmem releases and future gated horizons.
audience: Operator
---

# Release Readiness

<p className="stigmem-meta"><span>5 min read</span><span>Release engineer · Operator · Contributor</span><span>Release-line pivot</span></p>

<div className="stigmem-lead">

**What this page covers**

A single pivot for "what shipped in release X, what remains in release Y, and what's the gate between them." Active release rows mirror live GitHub milestones. Future beta, release-candidate, and GA rows are gated horizons from [ROADMAP.md](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md), not active milestones. For the deeper version-string conventions, see [ADR-001](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/001-versioning.md) and [ADR-019](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md).

</div>

**The release-line lattice:**

<div className="stigmem-grid">

<div><h4>v0.9.0aN</h4><p>Alpha series. Posture calibration + plugin extraction. <strong>v0.9.0a1 shipped</strong> 2026-05-08; <strong>v0.9.0a2 tagged</strong> 2026-05-18.</p></div>
<div><h4>Future beta line</h4><p>Hardened core, 30-day external operator soak. No active milestone today.</p></div>
<div><h4>Future release-candidate line</h4><p>Observation window after hardened-core exit. No active milestone today.</p></div>
<div><h4>Future GA line</h4><p>Wire format committed, compatibility commitment honored across the v1.x line. No active milestone today.</p></div>

</div>

---

## v0.9.0a3 — Alpha series continuation

<div className="stigmem-lead">

**Alpha-line catch-all after v0.9.0a2 artifact refresh.**

`v0.9.0a3` carries the next active alpha-line work: plugin-launch evidence ([#298](https://github.com/eidetic-labs/stigmem/issues/298)), security fixes, documentation and release-evidence cleanup, and operator-feedback iteration that lands before the future beta gate opens. Phase A plugin extraction and exit validation completed on `main`; v0.9.0a2 is tagged.

</div>

<div className="stigmem-fields">

<div>
<dt>Area</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Milestone</dt>
<dt><span className="stigmem-fields__type">open</span></dt>
<dd>Tracked at [milestone v0.9.0a3](https://github.com/Eidetic-Labs/stigmem/milestone/1), the only active release milestone.</dd>
</div>

<div>
<dt>CHANGELOG</dt>
<dt><span className="stigmem-fields__type">in flight</span></dt>
<dd>Active work tracked under `[Unreleased]` in [CHANGELOG.md](https://github.com/eidetic-labs/stigmem/blob/main/CHANGELOG.md). Promoted to `[0.9.0a3]` at tag time.</dd>
</div>

<div>
<dt>Entry</dt>
<dt><span className="stigmem-fields__type">ready</span></dt>
<dd>Phase A plugin extraction and exit validation complete on `main`; v0.9.0a2 tagged.</dd>
</div>

<div>
<dt>Exit</dt>
<dt><span className="stigmem-fields__type">pending</span></dt>
<dd>Ready to evaluate whether the future beta gate can open. See ROADMAP "Future beta line" for full beta-entry criteria.</dd>
</div>

</div>

---

## Future beta line — Hardened core

<div className="stigmem-lead">

**Hardened-core validation before any beta milestone opens.**

Scope per [ROADMAP future beta line](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md#future-beta-line--hardened-core-with-operator-validation): capability redesign, federation hardening, modular spec migration completion, OpenClaw safety, adversarial conformance corpus, storage immutability stack, operator-facing docs, and a 30-day external operator soak. No beta milestone is active today.

</div>

<div className="stigmem-fields">

<div>
<dt>Area</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Milestone</dt>
<dt><span className="stigmem-fields__type">future gate</span></dt>
<dd>No active beta milestone exists. Entry is blocked on alpha-line exit evidence.</dd>
</div>

<div>
<dt>Capability redesign ([ADR-003](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/003-prompt-injection.md))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Prompt-injection hardening surface.</dd>
</div>

<div>
<dt>Federation hardening ([ADR-004](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/004-federation-observability.md))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Audit retention/observability evidence landed in Phase A ([#435](https://github.com/eidetic-labs/stigmem/issues/435)); peer-trust + signature paths remain.</dd>
</div>

<div>
<dt>Modular spec migration ([ADR-010](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/010-modular-specs.md))</dt>
<dt><span className="stigmem-fields__type">partial</span></dt>
<dd>Structural migration shipped in Phase A; spec evolution continues.</dd>
</div>

<div>
<dt>Adversarial conformance corpus ([ADR-015](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/015-adversarial-conformance-and-model-certification.md))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Model certification track for stable-release readiness.</dd>
</div>

<div>
<dt>Storage immutability ([ADR-016](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/016-storage-immutability-enforcement.md))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>WORM stack + tombstone enforcement.</dd>
</div>

<div>
<dt>OpenClaw audit hardening</dt>
<dt><span className="stigmem-fields__type">in flight</span></dt>
<dd>Findings visible in the alpha/beta hardening lane; operator-validation track open.</dd>
</div>

<div>
<dt>Quality gates ([#437](https://github.com/eidetic-labs/stigmem/issues/437))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Dependency-currency reporting, file-size CI, stale internal-link lint, pytest markers, major-version hold register, branch/publish verification.</dd>
</div>

<div>
<dt>Contributor + demo readiness ([#438](https://github.com/eidetic-labs/stigmem/issues/438))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>`make demo` / `make demo-attack`, contributor architecture path, issue templates, engineering log, good-first issue tagging.</dd>
</div>

<div>
<dt>30-day operator soak ([#439](https://github.com/eidetic-labs/stigmem/issues/439))</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>At least one external operator running against the hardened core with public bug reporting. Operator recruitment ongoing per retraction-post invitation.</dd>
</div>

<div>
<dt>Exit</dt>
<dt><span className="stigmem-fields__type">pending</span></dt>
<dd>Threat-model risk register clean for stable-critical-path risks; OpenClaw audit findings all closed; 30-day soak completes with P0 findings addressed; release-candidate line ready to open.</dd>
</div>

</div>

---

## Future release-candidate line

<div className="stigmem-lead">

**Supply-chain hardening + external production usage.**

Scope per [ROADMAP future release-candidate and GA horizons](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md): sigstore-signed releases, reproducible builds, SBOM publication, three or more external operators in production, wire-format freeze candidate. No release-candidate milestone is active today.

</div>

<div className="stigmem-fields">

<div>
<dt>Area</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Milestone</dt>
<dt><span className="stigmem-fields__type">future gate</span></dt>
<dd>No active release-candidate milestone exists. Entry is blocked on future beta exit evidence.</dd>
</div>

<div>
<dt>Sigstore-signed releases</dt>
<dt><span className="stigmem-fields__type">in flight</span></dt>
<dd>Cosign keyless signing + SBOM attestation + Rekor evidence wired into publish workflow today; see [release verification](./release-verification).</dd>
</div>

<div>
<dt>Reproducible builds</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>BuildKit provenance present today; arbitrary-rebuild byte-for-byte reproducibility remains a scope note.</dd>
</div>

<div>
<dt>SBOM publication</dt>
<dt><span className="stigmem-fields__type">in flight</span></dt>
<dd>SPDX JSON SBOM attached to the GHCR image as an OCI referrer; cosign attestation present.</dd>
</div>

<div>
<dt>External production operators</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Three or more required for GA. Pipeline starts with the future beta soak invitation.</dd>
</div>

<div>
<dt>Wire-format freeze candidate</dt>
<dt><span className="stigmem-fields__type">not started</span></dt>
<dd>Conformance suite covers `v1.0/`; freeze finalizes at GA.</dd>
</div>

<div>
<dt>Exit</dt>
<dt><span className="stigmem-fields__type">pending</span></dt>
<dd>14-day rcN observation window without critical regression; ready to declare GA.</dd>
</div>

</div>

---

## Future GA line

<div className="stigmem-lead">

**Wire format committed; compatibility commitment honored across v1.x.**

Scope per [ROADMAP future release-candidate and GA exit criteria](https://github.com/eidetic-labs/stigmem/blob/main/ROADMAP.md#future-release-candidate-and-ga-lines): stable release shipped, wire format committed, compatibility commitment doc per [ADR-013](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md) honored across the v1.x line.

</div>

<div className="stigmem-fields">

<div>
<dt>Area</dt>
<dt><span className="stigmem-fields__type">Status</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt>Milestone</dt>
<dt><span className="stigmem-fields__type">future gate</span></dt>
<dd>No active GA milestone exists. Entry is blocked on the future release-candidate observation window completing without critical regression.</dd>
</div>

<div>
<dt>Wire format committed</dt>
<dt><span className="stigmem-fields__type">pending</span></dt>
<dd>Final freeze at GA.</dd>
</div>

<div>
<dt>Compatibility commitment ([ADR-013](https://github.com/eidetic-labs/stigmem/blob/main/docs/adr/013-deprecation-policy.md))</dt>
<dt><span className="stigmem-fields__type">pending</span></dt>
<dd>Deprecation policy honored across the v1.x line; breaking changes only at v2.0.</dd>
</div>

</div>

---

## How readiness is enforced

Three gates ensure release notes match shipped code:

1. **PR-closes-issue and milestone discipline** ([CONTRIBUTING.md](https://github.com/eidetic-labs/stigmem/blob/main/CONTRIBUTING.md#pr-closes-issue-and-milestone-discipline-from-v090a3-onward)) — every PR from v0.9.0a3 onward must close exactly one issue and assign the matching milestone. Lets anyone answer "what shipped in release X?" by reading the milestone view.
2. **`scripts/check_release_readiness.py`** — umbrella gate that asserts the CHANGELOG `[<version>]` section is non-empty and the corresponding milestone has zero open issues. Runs as a `release-readiness` job in `.github/workflows/publish.yml` ahead of every tag-gated publish job.
3. **Existing per-artifact gates** — [`check_version_consistency.py`](https://github.com/eidetic-labs/stigmem/blob/main/scripts/check_version_consistency.py), [`validate_version_surfaces.py`](https://github.com/eidetic-labs/stigmem/blob/main/scripts/validate_version_surfaces.py), [`check_release_evidence.py`](https://github.com/eidetic-labs/stigmem/blob/main/scripts/check_release_evidence.py), and the coverage/ruff/mypy/security-doc baselines — all run as part of CI.

---

*Updated as releases land. Last updated: 2026-05-21.*
