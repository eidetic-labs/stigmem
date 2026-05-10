# ADR-009: Repository file structure

**Status:** Accepted
**Date:** 2026-05-06 (revised 2026-05-07 to incorporate ADR-011 plugin architecture, ADR-016 immutability stack, and ADR-017 CIDs-as-core amendment)
**Authors:** Eidetic Labs
**Related:** ADR-002 (v1 critical-path scope), ADR-005 (docs IA), ADR-008 (experimental gates), ADR-011 (C1 plugin architecture), ADR-016 (storage immutability enforcement), ADR-017 (amendment to ADR-011: CIDs as core); `stigmem/analyses/repo-structure-review.md`

---

## Context

The v1.0 release left the repository with structure that reflects the broader scope question ADR-002 addresses:

- 41 entries at the root, vs. ~15–20 typical for a well-organized infrastructure project.
- Three locations for dashboard- and observability-related artifacts (`apps/dashboard/`, `dashboards/`, `deploy/grafana/`).
- Two Helm chart locations (`infra/helm/`, `deploy/helm/`).
- 13 spec versions at `spec/` root including the withdrawn v2.0 normative file.
- 12 adapters at peer level under `adapters/`; per ADR-002, only 2 (`mcp`, `openclaw`) are v1.0 critical-path.
- 3 SDKs at peer level under `sdks/`; per ADR-002, only 1 (`stigmem-py`) is critical-path.
- 9 deploy targets under `deploy/`; per ADR-002, only 1 (`compose`) is critical-path.
- No `experimental/` directory yet — ADR-002 and ADR-008 require one.
- Internal-only artifacts in public-facing surfaces: `dogfood/`, `tasks/todo.md`, `docs/video-scripts/`, the v1 launch blog post.
- The `node/src/stigmem_node/` module is well-organized internally; the sprawl is at the *repo* level, not inside the node module.

ADR-002 names what's in scope and out of scope. This ADR specifies how that scope decision manifests on disk: where deferred features live, how the top level is shaped, how docs are organized, and how the structure communicates the project's posture to anyone reading the repo cold.

The detailed analysis and per-directory recommendations live in `stigmem/analyses/repo-structure-review.md`. This ADR captures the load-bearing decisions and the rationale.

ADR-011 (revised 2026-05-07) committed to a C1 plugin architecture: cross-cutting features are implemented as plugin packages under `experimental/<feature>/`, registering against a hook system in core. ADR-017 (amendment to ADR-011) moved CIDs from plugin scope to core. ADR-016 added a storage immutability stack with substantial new core code. This ADR is updated to reflect those decisions: plugins are structurally distinct from adapters, plugin packages have a defined directory layout, and the core node module gains plugin infrastructure that this ADR's earlier "node/ stays as-is" framing did not anticipate.

## Decision

We adopt the following structural decisions.

### 1. Top-level shape

The repository root contains roughly 22 entries (down from 41), organized as:

- **Public adopter surface (root markdown files):** `README.md`, `LICENSE`, `LIMITATIONS.md`, `ROADMAP.md`, `SECURITY.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`.
- **Build/config files:** `pyproject.toml`, `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml`, `uv.lock`, `turbo.json`, `cliff.toml`, `Makefile`, `.python-version`, `.readthedocs.yaml`, `.mcp.json`, `.env.example`, `.gitignore`.
- **Critical-path code:** `node/` (includes the plugin-infrastructure subsystem per ADR-011), `adapters/` (mcp + openclaw only — adapters are clients of the recall API, distinct from plugins), `sdks/` (Python only), `deploy/` (compose only).
- **Critical-path assets:** `data/` (includes `data/conformance/adversarial/` per ADR-015), `docs/`, `spec/`, `site/`, `eval/`, `scripts/`.
- **Deferred work:** `experimental/` (six plugin packages per ADR-011 + non-plugin deferred items).
- **Single canonical demo entry:** `docker-compose.yml` (consolidate observability variant into a Compose profile rather than a peer file).
- **Test config:** `conftest.py`.
- **CI:** `.github/`.

Removed from root: `apps/`, `dashboards/`, `dogfood/`, `infra/`, `tasks/`, `docker-compose.observability.yml` (consolidated as a Compose profile).

### 2. `experimental/` is the canonical home for deferred features

Per ADR-002 and ADR-008, every deferred feature lives at `experimental/<feature>/` with a `STATUS.md` at the directory root tracking gate progress.

Two sub-categories of `experimental/<feature>/`:

**(a) Plugin packages** (per ADR-011 C1 architecture). Six cross-cutting features in this category: `lazy-instruction-discovery`, `time-travel`, `tombstones`, `memory-garden-acl`, `source-attestation`, `multi-tenant`. Each is a complete Python package that registers against the core hook system:

```
experimental/<feature>/                          # plugin package root
├── pyproject.toml                               # package manifest with [project.entry-points."stigmem.plugins"]
├── README.md                                    # plugin overview, install instructions, capability declarations
├── STATUS.md                                    # gate progress per ADR-008
├── src/
│   └── stigmem_plugin_<feature>/                # importable module
│       ├── __init__.py                          # exports `register(context) -> PluginManifest`
│       ├── handlers.py                          # hook handler implementations
│       └── config.py                            # Pydantic config schema
├── tests/                                       # plugin-specific tests
│   ├── test_handlers.py
│   └── test_integration.py
├── migrations/                                  # plugin's schema migrations (if any)
│   └── <NNN>_<description>.sql
├── integration/
│   └── README.md                                # hook contract: which hooks the plugin registers, capability declarations, configuration
└── conformance/                                 # plugin-specific conformance vectors
    └── <category>/...
```

The plugin's distribution is signed via Sigstore (production mode) per ADR-011 § Plugin trust and security model. The signed artifact is what operators install via `pip install stigmem-plugin-<feature>`.

**(b) Non-plugin deferred items.** Adapters, SDKs, deploy targets, and other deferred code that is not implemented as a stigmem-plugin package. These preserve their pre-extraction structure (e.g., `experimental/cognee-adapter/`, `experimental/sdk-go/`, `experimental/deploy-helm/`):

```
experimental/<item>/
├── STATUS.md                                    # gate progress per ADR-008
└── ... (code preserved as-is from v1.0)
```

The category-(a) plugin structure applies only to the cross-cutting feature plugins per ADR-011; adapters and other deferred code remain in their (b) shape.

**Note on CIDs (per ADR-017 amendment to ADR-011):** content-addressed fact IDs were originally scoped as a plugin in ADR-011's first revision. ADR-017 (2026-05-07) moved CIDs to core because they are load-bearing for ADR-003's trust boundary and ADR-016's immutability stack (L3). **CIDs do NOT appear under `experimental/`.** The CID code lives in `node/src/stigmem_node/cid.py` per the existing structure. The remaining six cross-cutting features remain plugins.

Top-level `experimental/` index:

```
experimental/
├── README.md                                    # index of all experimental features (plugins + non-plugin items)
├── STATUS-TEMPLATE.md                           # template for STATUS files
├── lazy-instruction-discovery/                  # plugin (a)
├── time-travel/                                 # plugin (a)
├── tombstones/                                  # plugin (a)
├── memory-garden-acl/                           # plugin (a)
├── source-attestation/                          # plugin (a)
├── multi-tenant/                                # plugin (a) — most complex
├── cognee-adapter/                              # non-plugin (b)
├── gemini-adapter/                              # non-plugin (b)
├── ... (other adapters per §3)
├── sdk-go/                                      # non-plugin (b)
├── sdk-ts/                                      # non-plugin (b)
├── deploy-helm/                                 # non-plugin (b)
├── ... (other deploy targets per §5)
└── dashboard/                                   # non-plugin (b)
```

### 2a. Plugins are not adapters

The repo distinguishes two kinds of extension code, and the directory layout reflects that:

| Concept | What it is | Where it lives | Examples |
|---|---|---|---|
| **Adapter** | A client of stigmem's recall/assert API. External system consumes stigmem's data. | `adapters/<name>/` (critical-path: mcp, openclaw) or `experimental/<name>-adapter/` (deferred). | MCP adapter, OpenClaw adapter, Cognee adapter, Obsidian plugin. |
| **Plugin** | A stigmem-extension package that registers against the core hook system per ADR-011. Extends what the protocol does. | `experimental/<feature>/` (per §2(a) above). | tombstones, time-travel, multi-tenant. |

A consequence: an adapter consuming stigmem's recall API does not register hooks. A plugin that adds new behavior to stigmem itself does not implement the recall client API. The two are structurally distinct concepts; they share the term "extension" loosely but the architecture separates them.

The Obsidian plugin (`experimental/obsidian-adapter/plugin/`) is named for Obsidian's plugin system; it is an adapter from stigmem's perspective. To avoid terminology confusion, this ADR and downstream docs use **"plugin"** exclusively to mean ADR-011 stigmem plugins, and **"adapter"** to mean stigmem clients.

### 3. Adapters: cut to two

`adapters/` contains only `mcp/` and `openclaw/` plus a README. Other adapters move:

| From | To |
|---|---|
| `adapters/cognee/` | `experimental/cognee-adapter/` |
| `adapters/gemini/` | `experimental/gemini-adapter/` |
| `adapters/letta/` | `experimental/letta-adapter/` |
| `adapters/obsidian/` | `experimental/obsidian-adapter/` |
| `adapters/obsidian-plugin/` | `experimental/obsidian-adapter/plugin/` |
| `adapters/openai-tools/` | `experimental/openai-tools-adapter/` |
| `adapters/paperclip/` | `experimental/paperclip-adapter/` |
| `adapters/zep/` | `experimental/zep-adapter/` |
| `adapters/boot-stubs/` | `experimental/lazy-instruction-discovery/boot-stubs/` (lives under the lazy-instruction-discovery plugin per ADR-011) |

The `clawhub-skill/` duplicate inside `adapters/openclaw/` is consolidated per OpenClaw audit M1.

### 4. SDKs: cut to one

`sdks/` contains only `stigmem-py/`. Go and TypeScript SDKs move to `experimental/sdk-go/` and `experimental/sdk-ts/`.

### 5. Deploy targets: cut to one

`deploy/` contains only `compose/` and `seccomp/` (the latter is used by Compose hardening). Other targets move:

| From | To |
|---|---|
| `deploy/helm/` | `experimental/deploy-helm/` |
| `deploy/fly/` | `experimental/deploy-fly/` |
| `deploy/systemd/` | `experimental/deploy-systemd/` |
| `deploy/grafana/` + `deploy/prometheus/` | `experimental/deploy-grafana/` (consolidated) |
| `deploy/paas/` | `experimental/deploy-paas/` |

### 6. Consolidate dashboard and observability

Three current locations consolidate to one experimental directory:

- `apps/dashboard/` (Next.js curator dashboard) → `experimental/dashboard/`.
- `dashboards/grafana/`, `dashboards/prometheus/` (JSON definitions) → `experimental/deploy-grafana/dashboards/`.
- `deploy/grafana/`, `deploy/prometheus/` (provisioning) → `experimental/deploy-grafana/`.

After consolidation, `apps/` and `dashboards/` directories are removed.

### 7. Resolve `infra/`

`infra/docker-compose.soak.yml` → `eval/soak/docker-compose.soak.yml` (it's a soak-test rig, not a deploy target).
`infra/fly.toml`, `infra/fly.dashboard.toml` → `experimental/deploy-fly/`.
`infra/helm/` → merged with `deploy/helm/` into `experimental/deploy-helm/` (resolve duplication).
`infra/soak/` → `eval/soak/`.

After moves, `infra/` is removed.

### 8. Spec reorganization

```
spec/
├── README.md # Index pointing at current and listing archive
├── CHANGELOG.md # Version history
├── stigmem-spec.md # The CURRENT spec (one file, no version suffix)
├── archive/ # All historical and superseded specs
│ ├── stigmem-spec-v0.2.md
│ ├── stigmem-spec-v0.3-draft.md
│ ├── ... (all v0.x drafts)
│ ├── stigmem-spec-v1.0.md # Superseded; preserved for reference
│ ├── stigmem-spec-v1.1-draft.md
│ └── stigmem-spec-v2.0.md # Superseded; preserved for reference
├── design/ # Existing — keep
└── security/ # Existing — threat-model.md lives here
```

`spec/stigmem-spec-v0.9-section-17-memory-garden-draft.md` moves to `experimental/17-memory-garden/spec.md` — it's a draft for a deferred feature.

### 9. `docs/` reorganization per ADR-005

`docs/docs/` reorganizes into the four-tab IA: Learn / Build / Operate / Secure. Sidebars and versioning update accordingly.

`docs/versioned_docs/` updates to add `version-v0.9.0-preview/` and removes or archives `version-v0.2/` and `version-v1.1/`.

Top-level `docs/*.md` operational artifacts move:

- `docs/cursor-reset-recovery.md` → either `docs/operate/troubleshooting.md` or removed.
- `docs/failure-modes-4node.md` → `docs/operate/runbooks/4node-failure-modes.md`.
- `docs/soak-report-4node.md` → `eval/soak/reports/4node-2026-XX.md`.
- `docs/video-scripts/` → out of the docs tree (private repo or `dogfood/`).

The v1.0 launch blog post (`docs/blog/2026-05-03-stigmem-v1-launch.md`) is **bannered in place** with a pointer to the migration post, not deleted, to preserve external link history.

### 10. Add the missing top-level docs and fix LICENSE

- `LIMITATIONS.md` (already drafted) — operator-facing limitation statement.
- `MAINTAINERS.md` (already drafted at `Internal-Comms/stigmem/public/MAINTAINERS.md`) — current founder + founding-team placeholder.
- `ROADMAP.md` — public roadmap derived from the strengthening plan.
- `docs/adr/` directory containing all 18 ADRs.
- **`LICENSE` — replace.** Verification 2026-05-07 found that the current `LICENSE` file has ~10 substantive deviations from the canonical Apache-2.0 SPDX text (§1 definitions, §3 patent grant, §4 NOTICE clause, §4 sublicense wording, §7 word changes, §8 damages list and "exemplary" vs "consequential", §9 heading). These are not formatting drift; they are legally distinct text. Canonical replacement is staged at `Internal-Comms/stigmem/public/LICENSE` (canonical Apache-2.0 with `Copyright 2026 Eidetic Labs` substituted in the Appendix). Lands during Phase A PR 1.

### 11. Remove or relocate internal-only artifacts

- `dogfood/` — split per the founder review (2026-05-07):
  - `dogfood/migrate_ceo_memory.py` — genericize to `scripts/import_markdown_tree.py`. The pattern (markdown index + frontmatter → facts) is generally useful; the original was hardcoded to one personal use case (`user:ceo`, `company` scope, `agent:stigmem-migrator`). The genericized version takes `--entity`, `--scope`, `--source`, `--relation-prefix`, `--default-type`, `--confidence`, `--index-file` as CLI arguments. Drafted at `Internal-Comms/stigmem/tooling/import_markdown_tree.py`; lands in stigmem `scripts/` during Phase A PR 3.
  - `dogfood/snapshot.sh` — relocate to `scripts/stigmem-snapshot.sh`. Genericized version takes `--scope`, `--entities` (comma-separated list), `--output` as CLI args; `company:acme` placeholder removed; auth via `STIGMEM_API_KEY` env or `--api-key`; supports `--limit` and `--no-contradictions` flags; documented examples include cron usage. Drafted at `Internal-Comms/stigmem/tooling/stigmem-snapshot.sh`; lands in Phase A PR 3.
  - `dogfood/devto-lazy-discovery-tokenomics.md` — already published externally on dev.to; remove from repo or move to `docs/blog/archive/`. Founder's call.
  - `dogfood/README.md` — content splits into operator-doc sections that ship with each script.
  - **Net: `dogfood/` directory disappears entirely from the v0.9.0-preview repo.** Useful patterns extracted; personal/CEO-specific framing removed.
- `tasks/todo.md` — remove. Use GitHub Projects or a private repo for in-flight TODOs.
- `docs/blog/devto-post-v1-launch.txt` — remove or archive under `docs/blog/archive/`.

### 12. `node/` module: gains plugin infrastructure (per ADR-011) and immutability stack (per ADR-016)

`node/src/stigmem_node/` had good internal organization in v1.0. This ADR does **not** propose a cosmetic restructure. But ADR-011 and ADR-016 add substantial new core code that needs a home in `node/`:

**Plugin infrastructure (per ADR-011), added in Phase A:**

```
node/src/stigmem_node/
├── plugins/                    # plugin-system core code (new)
│   ├── __init__.py
│   ├── registry.py             # HookRegistry, band-based composition
│   ├── manifest.py             # PluginManifest schema and validation
│   ├── context.py              # PluginContext with capability-restricted accessors
│   ├── lifecycle.py            # registration, validation, health monitoring
│   ├── signing.py              # Sigstore verification at registration
│   ├── audit.py                # plugin registration audit events
│   ├── hooks/                  # hook protocol definitions
│   │   ├── voting.py
│   │   ├── filter_chain.py
│   │   ├── score_delta.py
│   │   └── fire_and_forget.py
│   └── capabilities.py         # capability allowlist
├── cid.py                      # CIDs (core per ADR-017, not a plugin)
├── ... (existing modules)
```

**Immutability stack (per ADR-016), added in Phase B:**

```
node/src/stigmem_node/
├── chain/                      # local hash chain (L4)
│   ├── __init__.py
│   ├── computer.py             # chain computation on fact insert
│   ├── verifier.py             # chain verification
│   └── proof.py                # chain proof construction for recall responses
├── transparency/               # Sigstore Rekor integration (L5)
│   ├── __init__.py
│   ├── client.py               # Rekor SDK wrapper
│   ├── checkpointer.py         # async checkpoint commit
│   └── inclusion_proof.py      # proof construction and verification
├── projections/                # projection tables (L1) for previously-mutable fields
│   ├── __init__.py
│   ├── validity.py             # fact_validity_overrides
│   ├── embedding_status.py     # fact_embedding_status
│   └── ... (one per former UPDATE facts call site)
└── ... (existing modules)
```

**Conformance-corpus runner (per ADR-015), added in Phase B:**

```
scripts/run_adversarial_conformance.py    # not under node/; CLI tool for model certification
```

A separate follow-up audit decides which existing individual `*.py` files in the module correspond to deferred features (`billing.py`, `instruction_migrate.py`, `fuzzy_resolver.py`, `graph_index.py`, `card_materializer.py`) and whether they should move under `experimental/<feature>/`. That audit lands after this ADR's PRs settle. Note that some of these files (e.g., `instruction_migrate.py`) are likely already absorbed into the `lazy-instruction-discovery` plugin per ADR-011; the audit confirms.

## Alternatives considered

**1. Update ADR-002 with the file-layout decisions instead of writing a new ADR.** Rejected. ADR-002 is the *scope* decision; this ADR is the *layout* decision. They are separable: a reader could agree with one and disagree with the other. Combining them obscures which decision is being challenged when scope or layout is later revisited. Per ADR-DEFINITION, one decision per ADR.

**2. Restructure the `node/src/stigmem_node/` module in the same pass.** Rejected. The module is well-organized internally; restructuring for cosmetic consistency is not a payoff. A targeted follow-up audit can move individual deferred-feature files to `experimental/` once the repo-level cuts are done and the scope of work is clearer.

**3. Delete deferred features rather than moving them to `experimental/`.** Rejected. ADR-008 commits to feature reintroduction through gates. Deletion forecloses on that. The `experimental/` directory is the cost of preserving the optionality.

**4. Land the entire restructure as one large PR.** Rejected. The change touches workspace configs, CI, docs IA, and ~50 directory moves. A single PR is unreviewable. Three sequential PRs (cuts → cleanup/ADRs → docs IA) keep diffs reviewable and let CI confirm correctness at each step.

**5. Wait until v1.0.0 GA to do the structural cleanup.** Rejected. The current structure actively confuses anyone evaluating the project. It also makes the strengthening plan's other Phase A deliverables harder to land cleanly. Doing this now is the lowest-cost moment.

## Consequences

### What gets easier

- **Top-level reads as a coherent project.** A first-time visitor to the repo sees a small, navigable surface. The `experimental/` directory exists and is clearly labeled; the critical-path code is in obvious locations.
- **The scope contract becomes physically obvious.** ADR-002 says what's in v1.0; the file structure visibly enforces it. Anyone proposing scope creep has to add a directory to `adapters/`, `sdks/`, or `deploy/` — which is a friction-producing PR rather than a one-line change.
- **Gate progression for deferred features is structurally tracked.** Each `experimental/<feature>/STATUS.md` is the single source of truth for that feature's progress.
- **Default builds, default tests, and default docs become well-defined.** The Python workspace, pnpm workspace, and Turbo config exclude `experimental/`. A clean clone + `make demo` + `pytest` runs against the v1.0 critical-path; experimental features require explicit opt-in.
- **Future restructuring is structural, not stylistic.** Any further reorganization happens via amendments to this ADR, not ad-hoc.

### What gets harder

- **Migration cost.** Three PRs of structural moves, plus updates to imports, workspace configs, CI workflows, and any external links pointing at moved files. Mitigated by Docusaurus redirects and by sequencing the PRs to keep each one reviewable.
- **Operators of v1.0** who built against `adapters/letta/` (or any other moved adapter) will find their installs broken at the import path. Mitigated by the migration notice — those operators are already being told to migrate to v0.9.0-preview, and the migration story includes import-path changes.
- **Discoverability of experimental features.** A user who wants to find the Postgres backend can no longer find it at `deploy/`. Mitigated by `experimental/README.md`, by clear cross-references from the docs and from ADR-002, and by the migration post which names the new location.
- **Existing IDE workspaces and build tooling on contributors' machines** assume the current structure. Anyone with a checkout will need to refresh paths after the moves land.

### New risks

- **R-STRUCT-1: link rot from external sources.** The v1 announcement, blog posts, and any third-party references that pointed at moved files will break. Mitigation: Docusaurus supports redirects; the migration post explicitly addresses migration; the most-linked-to file (the v1 blog post) is bannered in place.
- **R-STRUCT-2: incomplete cuts.** A subsequent feature could land in the wrong place because the contributor wasn't aware of ADR-002 / this ADR. Mitigation: PR template asks "does this PR add a file at the top level or under `adapters/`, `sdks/`, `deploy/`? If so, link the ADR-002 amendment that authorized it."
- **R-STRUCT-3: experimental code rotting.** Code in `experimental/` that nobody touches develops bugs that emerge years later when reintroduction is attempted. Mitigation: per ADR-008, experimental features are buildable but not part of the test matrix; reintroduction (which requires gate 3, conformance vectors) brings them up to v1.x quality.

## Implementation plan

Three sequential PRs, all in Phase A of the strengthening plan, ideally landed across the Phase A PR sequence.

### PR 1 — Create `experimental/` and move out-of-scope code

- Create `experimental/` with `README.md` and `STATUS-TEMPLATE.md`.
- Move adapters, SDKs, deploy targets, dashboard, infra contents per the decisions above.
- Resolve duplicate Helm chart by inspecting both copies and merging into `experimental/deploy-helm/`.
- Update `pyproject.toml` workspace members, `pnpm-workspace.yaml`, `turbo.json` to exclude `experimental/` from default builds.
- Update CI workflows (`ci.yml`, `conformance.yml`, etc.) to skip experimental in default jobs.
- Update `Makefile` (`make demo`, `make test`) to operate against the cut surface.
- Run full test suite to confirm v1.0 critical-path still builds and passes.

This PR is large but mechanical. Most of it is `git mv` plus workspace-config updates.

### PR 2 — Spec reorganization, top-level cleanup, ADRs

- Move spec drafts to `spec/archive/evolution/` (per master-checklist §4.3a — evolutionary snapshots, not "design drafts"; spec content forward-migrated, not archived as history).
- Designate canonical spec at `spec/stigmem-spec-v0.9.0-preview.md`.
- Move `spec/stigmem-spec-v0.9-section-17-memory-garden-draft.md` to `experimental/memory-garden-acl/spec.md` (per ADR-011 plugin naming).
- Remove `dogfood/`, `tasks/`, `infra/` after content moves.
- Remove `apps/`, `dashboards/` after content moves.
- Banner the v1 blog post in place with a pointer to the migration post.
- Add `docs/adr/` with all 17 ADRs plus `README.md`.
- Add `LIMITATIONS.md`, `ROADMAP.md`, and `MAINTAINERS.md` at root.
- Remove `docs/blog/devto-post-v1-launch.txt`.

### PR 3 — Docs IA restructure

- Restructure `docs/docs/` into Learn / Build / Operate / Secure (per ADR-005).
- Update `docs/sidebars.js`.
- Update `docs/versioned_docs/` to add `version-v0.9.0-preview/`.
- Move top-level `docs/*.md` operational files to their proper homes (per the structure review).
- Move `docs/video-scripts/` out of the docs tree.
- Update `docs/blog/` to reflect the retraction.

### Verification (every PR)

After each PR:

- `make demo` works on a clean machine.
- `pytest` against v1.0 critical-path passes.
- `python scripts/check_version_consistency.py` passes.
- CI is green.
- Linkrot check: any moved file linked from external docs has a redirect or the linker is updated.

## Amendment process

This ADR captures the structural decisions for v1.0. Changes to the layout require:

1. A new ADR titled "Amendment to ADR-009: [scope of change]".
2. Sign-off per ADR-001 §Contributor approval rule (two contributors or the founder alone).
3. Coordination with ADR-002 if the change reflects a scope-decision change, or with ADR-011 if the change reflects a plugin-architecture change.

Routine internal changes within `node/`, `adapters/<existing>/`, or `experimental/<feature>/` do not require amendments — only changes to the top-level layout or to which features live where.

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*