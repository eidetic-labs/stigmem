# Release cadence

How stigmem publishes a new release. Internal-facing maintainer doc; not part of the public docs site.

This document is a **runbook**, not a policy. The policy (versioning rules, phase mapping, stability commitments) lives in [ADR-001](../../docs/adr/001-versioning.md), [ADR-019](../../docs/adr/019-amendment-to-adr-001-prerelease-version-strings.md), and `release/version-surfaces.yaml`. This doc describes the operational sequence a maintainer follows to ship.

---

## Audience

A maintainer with publish rights (founder during Phase A) preparing a new tagged release of stigmem. Assumes you've already merged the work into `main` and CI is green.

---

## Pre-release checklist

Before pushing a tag, verify:

- [ ] All open PRs that should ship in this release are merged into `main`.
- [ ] CI is green on the latest `main` commit.
- [ ] `python scripts/check_version_consistency.py` passes locally (CI also runs this).
- [ ] `release/version-surfaces.yaml` reflects every surface this release publishes to.
- [ ] `CHANGELOG.md` has a top entry for the new version, drafted and reviewed.
- [ ] If this release introduces breaking changes, the changelog entry includes a clearly-marked `### BREAKING` subsection.
- [ ] If this release closes any GitHub issues, those issues are linked from the CHANGELOG entry.
- [ ] `MAINTAINERS.md § Credential rotation` table is up to date — no expired tokens.
- [ ] Any pending Trusted Publisher (PyPI) configurations for new packages added in this release are registered at pypi.org.

If any item fails, fix or document before proceeding.

---

## Version-string sweep

Every published version string in the repo must agree with the new release. The version-consistency CI gate (per ADR-019) catches most of this; this section documents the human-driven updates.

**File-backed surfaces** (caught by CI):

- `pyproject.toml`, `node/pyproject.toml`, `sdks/stigmem-py/pyproject.toml`, `adapters/openclaw/pyproject.toml` — PEP 440 form (e.g. `0.9.0a2`).
- `package.json`, `sdks/stigmem-ts/package.json` — semver form (e.g. `0.9.0-alpha.2`).
- `infra/helm/stigmem/Chart.yaml`, `deploy/helm/stigmem/Chart.yaml` — `appVersion` in semver form.

**Documentation surfaces** (currently CI-skipped; sweep manually):

- `README.md` status banner, install commands, badges.
- `CHANGELOG.md` top entry.
- `LIMITATIONS.md` "Applies to" line.
- `SECURITY.md` "Applies to" line + Supported Versions table.
- `docs/docs/community/security-disclosure.md` Supported Versions table.
- `node/src/stigmem_node/main.py` FastAPI(version=) string.
- `docs/openapi/stigmem.json` `info.version` (regenerate via `uv run python scripts/export_openapi.py`).
- `node/src/stigmem_conformance/__init__.py` `__version__`.
- `eval/README.md` baseline JSON `server_version` example.
- `deploy/systemd/README.md` `pip3 download` example.
- `adapters/openclaw/clawhub-skill/SKILL.md` (if cutting a new ClawHub skill release alongside).

**Compose surfaces** (added to release cadence on 2026-05-09):

- `docker-compose.yml` — both `node-a` and `node-b` `image:` fields. Use the new tag (e.g. `ghcr.io/eidetic-labs/stigmem-node:0.9.0a2`). Compose still falls back to local build if the image can't be pulled (e.g. on a dev branch before the image exists), so this update is forward-looking but doesn't break older clones.

---

## Tag and trigger publish

```bash
# Confirm working copy clean
git status

# Confirm you're on main with the latest
git fetch origin
git log --oneline main..origin/main  # should be empty
git pull --ff-only origin main

# Tag with the PEP 440 shorthand (per ADR-019)
git tag v0.9.0a2          # adjust version
git push origin v0.9.0a2
```

Pushing the tag triggers `.github/workflows/publish.yml`, which fans out into:

1. **`publish-node`** — multi-arch (linux/amd64 + linux/arm64) GHCR image; Sigstore cosign keyless signed; SBOM (SPDX JSON) attached.
2. **`publish-dashboard`** — same shape for the Next.js dashboard.
3. **`publish-sdk-ts`** — npm publish of `@eidetic-labs/stigmem-ts` with `--tag <alpha|beta|rc|latest>` derived from the version, with provenance attestation via OIDC.
4. **`publish-python`** — matrix publishes `stigmem`, `stigmem-py`, `stigmem-node`, `stigmem-openclaw` to PyPI via Trusted Publishers (OIDC; no API token).

All four jobs run in parallel. Total runtime ~5-8 minutes.

---

## Post-publish verification

Within ~5 minutes of tag push:

- [ ] **PyPI** — `pip install --pre stigmem` resolves to the new version. `pip show stigmem` returns the expected `Version:`. Repeat for `stigmem-py`, `stigmem-node`, `stigmem-openclaw`.
- [ ] **npm** — `npm view @eidetic-labs/stigmem-ts version` returns the new semver. `npm view @eidetic-labs/stigmem-ts` shows the right `dist-tags` (the new prerelease should be on `alpha`/`beta`/`rc`, not `latest`).
- [ ] **GHCR** — `docker pull ghcr.io/eidetic-labs/stigmem-node:<tag>` succeeds. Same for `stigmem-dashboard`.
- [ ] **GHCR visibility** — for first publish of a new package only: visit `https://github.com/orgs/Eidetic-Labs/packages` → find the package → Package settings → Danger Zone → Change visibility → **Public**. Subsequent pushes inherit the visibility setting; this is one-time per package.
- [ ] **Cosign** — `cosign verify --certificate-identity-regexp 'github.com/Eidetic-Labs/stigmem' --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' ghcr.io/eidetic-labs/stigmem-node:<tag>` succeeds.
- [ ] **GitHub release** — Created automatically by the tag; verify the release page exists at `https://github.com/Eidetic-Labs/stigmem/releases/tag/v0.9.0a2` and links to the CHANGELOG entry.

Within ~2 hours of tag push:

- [ ] **piwheels** mirror — `https://www.piwheels.org/project/stigmem-py/` shows the new version with ARM wheels.
- [ ] **npm CDN mirrors** — `curl -sI https://unpkg.com/@eidetic-labs/stigmem-ts@<semver>/package.json` returns 200.

---

## ClawHub publish (manual)

ClawHub doesn't auto-publish from CI. Maintainer pushes the new skill version from their machine:

```bash
cd adapters/openclaw/clawhub-skill
# Update version: in SKILL.md to next iteration (independently versioned;
# does NOT match canonical line — see notes in SKILL.md).
# Update package: in SKILL.md to the new stigmem-py range if changed.
openclaw skills push
```

If the ClawHub skill pins a `stigmem-py` version range that doesn't yet exist on PyPI, this push will succeed (ClawHub doesn't validate transitive Python deps), but `openclaw skills install stigmem-node` will fail at the dep-resolution step. So push ClawHub *after* PyPI publish is confirmed working.

---

## Rollback

PyPI, npm, GHCR each have different retraction mechanics:

| Surface | Mechanism | Time-bounded? |
|---|---|---|
| **PyPI** | `twine yank` (PEP 592) — or via pypi.org Web UI Manage page | No time limit; reversible |
| **npm** | `npm unpublish <pkg>@<ver>` (within 72 hours of publish) or `npm deprecate <pkg>@<ver> "msg"` (anytime) | unpublish is 72h-bound; deprecate has no time limit |
| **GHCR** | Image manifests stay forever (immutable). Tag can be deleted but pulled image references resolve from local cache. Best response is to publish the next version with the fix. | Effectively no rollback |
| **ClawHub** | No yank mechanism. Push next skill version with corrected pin/content; reach out to ClawHub admin for last-resort delete. | No rollback |

**General rollback principle:** publishing the *next* version with a fix is almost always preferable to retracting the bad one. PyPI and npm are exceptions where yanking is appropriate signaling for "broken release that adopters shouldn't reach for." For GHCR, fix-forward.

If a release is found broken post-publish:

1. **File a tracking issue** explaining the breakage and the chosen response.
2. **Yank** PyPI versions where appropriate (PEP 592). **Deprecate** npm versions where appropriate.
3. **Publish the fix** as the next version (e.g., 0.9.0a2 follows 0.9.0a1) — never reuse a version number.
4. **Update CHANGELOG** with both entries: the broken version with a brief callout, and the fix version with the diff from the broken one.
5. **Notify** if the broken version was widely-installed: post to the GitHub Discussions / Issues tracker.

See ADR-019 for why version numbers are immutable across all our surfaces (PEP 440 / npm both forbid republish under the same number).

---

## Annual review

This document is reviewed once per major release cycle (Phase A → B, B → C, C → GA, etc.) to incorporate operational lessons. Last reviewed: **2026-05-09** (created — Phase A in progress).
