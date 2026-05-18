# PR 4a integration analysis

Issue: [#290](https://github.com/eidetic-labs/stigmem/issues/290)
Parent: [#289](https://github.com/eidetic-labs/stigmem/issues/289)

## Decision

The stable PR 4-INF hook surface is almost sufficient for extracting
`Spec-X1-Lazy-Instruction-Discovery` into
`stigmem-plugin-lazy-instruction-discovery`, but implementation should add one
small hook-site correction before moving behavior:

- The fact-query path already fires `pre_recall_authorize`,
  `pre_recall_rewrite`, `recall_filter`, `recall_rank`, and
  `post_recall_audit`.
- The `/v1/recall` route does not yet fire recall hooks around its
  `RecallRequest` or `ScoredFact` pipeline.
- No new hook names are needed. PR 4a should wire the existing recall hooks
  into the `/v1/recall` route before relying on plugin handlers for
  instruction recall.

No ADR-011 amendment is required for PR 4a. The 22-hook surface remains the
right boundary.

## Current core surface

Lazy instruction discovery is still implemented in core:

- `node/src/stigmem_node/routes/instruction.py`
  - `GET /v1/agents/{agent_id}/boot-stub`
  - `GET /v1/agents/{agent_id}/instruction-manifest`
  - `PUT /v1/agents/{agent_id}/instruction-manifest`
  - `POST /v1/agents/{agent_id}/recall-instruction`
  - `POST /v1/instruction/audit`
  - `GET /v1/agents/{agent_id}/instruction-manifest/coverage`
- `node/src/stigmem_node/models/instruction.py`
- `node/src/stigmem_node/instruction_migrate.py`
- `node/src/stigmem_node/cli/parser.py` instruction and discovery-audit
  commands
- `node/migrations/021_instruction_discovery.sql`
- `node/tests/test_phase10_instruction.py`
- `node/tests/test_instruction_migrate_b2.py`
- `data/conformance/v2.0/21_instruction_discovery.json`

`node/src/stigmem_node/main.py` currently imports and mounts
`instruction_router` unconditionally. That is the behavior PR 4a must remove
from the default install.

## Extraction target

The plugin should live under `experimental/lazy-instruction-discovery/` with a
Python package that exposes a `stigmem.plugins` entry point returning a
`PluginManifest`.

Recommended package shape:

```text
experimental/lazy-instruction-discovery/
  pyproject.toml
  src/stigmem_plugin_lazy_instruction_discovery/
    __init__.py
    manifest.py
    config.py
    routes.py
    recall.py
    migrate.py
    migrations/
      001_instruction_discovery.sql
  tests/
    test_manifest.py
    test_registration.py
    test_routes.py
    test_default_install.py
    test_hook_order.py
```

The existing boot-stub templates, tutorial, spec, status, and security files
should remain colocated with the feature.

## Hook usage

### `pre_recall_authorize`

Use this for plugin-owned authorization checks that must fail closed before an
instruction recall or instruction manifest read proceeds. The seed issue did
not list this hook, but the current core implementation performs explicit
agent-access checks, so the plugin needs an equivalent pre-read guard.

Inputs should include:

- `identity`
- `tenant`
- `request_id`
- an instruction-specific query payload containing `agent_id`, route/action,
  requested scope, and manifest version when present

### `pre_recall_rewrite`

Use this only after `/v1/recall` hook wiring accepts a mutable payload for
normal recall requests. Lazy instruction discovery should use it to constrain
instruction retrieval to the plugin-computed `instruction:` scope and manifest
intent.

The existing fact-query hook accepts a dictionary. PR 4a should use the same
pattern for `RecallRequest`-derived data rather than introducing a new hook.

### `recall_filter`

Use this to drop facts that are not eligible instruction chunks after the core
recall pipeline has applied ordinary scope, trust, tombstone, and garden checks.
This keeps instruction-specific filtering in the plugin while preserving core
defenses.

### `recall_rank`

Optional. The plugin can initially preserve the current manifest scoring
behavior inside plugin code. If it needs to bias normal recall results by
manifest hints, use `recall_rank` instead of creating a new ranking hook.

### `post_recall_audit` and `audit_emit`

Use `post_recall_audit` for ordinary recall-path audit metadata and `audit_emit`
for plugin-specific discovery audit events. The current `instruction_audit`
table is feature-specific, so plugin-owned audit writes can remain in the
plugin and emit registry audit events for observability.

### `migration_register`

Move the `instruction_manifests`, `instruction_audit`, and `boot_stubs` schema
from core migration `021_instruction_discovery.sql` into plugin migrations.

The plugin migration should use its own migration ids under the plugin
migration lifecycle, not core migration number `021`. PR 4a should preserve
upgrade behavior for existing alpha databases by either:

- leaving core migration `021` as an inert compatibility migration that creates
  nothing new on fresh installs, while the plugin owns future schema creation;
  or
- adding an explicit migration handoff note and tests that prove existing
  tables are accepted as already present by the plugin migration.

The first option is less risky for existing local alpha users.

## Capability requirements

Declare these plugin capabilities in the manifest:

- `facts.read` — fetch instruction facts referenced by a manifest
- `facts.write` — publish instruction manifests as facts and migrate instruction
  markdown into facts
- `recall.read` — invoke or wrap recall behavior for instruction retrieval
- `audit.emit` — emit discovery audit and plugin audit records
- `audit.read` — read discovery audit reports for operator CLI output
- `config.read` — read plugin configuration

The seed issue listed `facts.read`, `recall.read`, and `audit.emit`. Current
core behavior also writes manifests/facts and reads audit data, so
`facts.write` and `audit.read` are required unless PR 4a deliberately splits
write/report commands into later issues.

Do not add a new capability name for `instruction_write` in PR 4a. ADR-003
still owns that model. Until ADR-003 is implemented, the plugin must remain
experimental and fail closed for production use.

## Config schema

The plugin config schema should include:

- `enabled: bool = False`
- `allow_manifest_publish: bool = False`
- `allow_instruction_recall: bool = False`
- `allow_file_path_entries: bool = False`
- `max_manifest_tokens: int = 1000`
- `max_boot_stub_tokens: int = 500`
- `max_guaranteed_units: int = 5`
- `audit_token_ttl_seconds: int = 86400`
- `adapter_profiles: list[str]`

Default config must keep lazy instruction discovery disabled. Operators should
have to opt in explicitly.

## Implementation path

1. Add `/v1/recall` hook-site wiring for the existing recall hooks.
2. Add plugin package scaffold, manifest, config schema, and discovery tests.
3. Move instruction route handlers, models, migration helpers, and CLI handlers
   into the plugin package.
4. Remove unconditional `instruction_router` mounting from core. If alpha
   compatibility requires a stub, make it return a clear disabled/not-installed
   response without executing discovery behavior.
5. Move instruction-specific migrations to `migration_register` and add tests
   for fresh plugin install plus existing-table compatibility.
6. Add no-plugin tests proving default installs do not expose active lazy
   instruction discovery.
7. Add plugin-loaded tests proving lazy instruction behavior and deterministic
   hook ordering.

## Validation plan

Local validation for the implementation PRs should include:

- plugin discovery and manifest validation tests
- no-plugin default install API/CLI tests
- plugin-loaded route tests for manifest publish, manifest read, boot-stub
  generation, recall-instruction, audit submit, and coverage report
- migration tests for plugin schema registration and checksum tracking
- conformance vectors with no plugin loaded
- plugin-loaded lazy instruction integration tests
- hook ordering tests covering `pre_recall_authorize`, `pre_recall_rewrite`,
  `recall_filter`, `post_recall_audit`, and `migration_register`

## Artifact evidence

PR 4a implementation is landing before a signed/package-published lazy
instruction discovery plugin artifact. Artifact publication and signing evidence
are explicitly queued in
[#298](https://github.com/eidetic-labs/stigmem/issues/298). Until that issue is
closed, the plugin is source-available under `experimental/` for validation only
and must not be described as a released installable plugin artifact.

## Risks and blockers

- `Spec-X1` is still marked blocked on ADR-003. PR 4a can extract the feature
  into an opt-in experimental plugin, but it must not claim production support
  or ADR-008 graduation.
- The existing `/v1/recall` route lacks recall hook wiring; this is an
  implementation prerequisite, not an ADR blocker.
- Moving core migration `021` requires compatibility care for existing alpha
  databases.
- Current route behavior uses admin checks and broad `instruction:` scope
  semantics that predate ADR-003. The plugin should preserve alpha behavior
  only behind explicit opt-in config and document that hardened instruction
  authorization remains Phase B work.
