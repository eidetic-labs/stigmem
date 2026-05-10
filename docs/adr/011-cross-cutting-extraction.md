# ADR-011: Plugin architecture for cross-cutting features (C1)

**Status:** Accepted
**Amended by:** ADR-017 (2026-05-07) — CIDs reclassified from plugin to core; six remaining cross-cutting plugins. ADR-011's body is preserved as the historical record; readers should consult ADR-017 for the current scope of plugins-vs-core.
**Date:** 2026-05-07
**Authors:** Eidetic Labs
**Supersedes:** ADR-011 (revised 2026-05-06, direct-to-C2)
**Related:** ADR-002 (v1 scope), ADR-008 (experimental gates), ADR-009 (repo structure), ADR-010 (modular specs), ADR-012 (version-aware feature exposure), ADR-013 (deprecation policy); `stigmem/analyses/feature-extraction-analysis.md`

---

## Context

ADR-009 establishes `experimental/<feature>/` as the home for deferred features. ADR-002 names which features are deferred. The implicit assumption — that moving a feature to `experimental/` is a `git mv` — holds for ~75% of features but fails for the cross-cutting ones (tombstones, time-travel, CIDs, multi-tenant, lazy instruction discovery, memory-garden advanced ACL, source attestation), which are woven into the core node module with dozens of references in single files.

This ADR commits to the strategy for handling cross-cutting features: which architectural pattern the project uses, how features integrate with core, what the plugin development model looks like, and how security and scalability are guaranteed at the architectural level rather than per-plugin.

The choice is between three approaches, in increasing order of architectural cleanliness and upfront cost:

- **Option C3 (feature flags only):** implementation stays in core, gated by feature flags. Scope contract leak; security surface includes all deferred features regardless of whether enabled.
- **Option C2 (thin shims):** implementation lives in `experimental/<feature>/`; core has named integration points that no-op when the experimental package isn't installed. Cleaner code surface; integration points are feature-specific.
- **Option C1 (plugin architecture):** core has no awareness of specific features; all integration happens via a generic hook/registry system. Plugins register themselves and provide implementations. Cleanest architecture; substantial upfront design work.

**Two prior versions of this ADR proposed C3-then-C2 and direct-to-C2. After founder review, both are superseded.** The reasoning: if C1 is the long-term architectural destination, doing C2 first means refactoring twice. The "do it once" principle that argued against C3-then-C2 also argues against C2-then-C1. Stigmem commits to C1 from Phase A.

The cost is real — C1 requires designing a plugin infrastructure before any feature extracts — but the benefit is a single architectural commitment that doesn't need revisiting and a security/scalability story that the architecture itself enforces rather than each feature reproducing independently.

## Decision

We adopt **Option C1: a plugin architecture** for all cross-cutting features. The architecture is committed in this ADR with the design specifics below. All seven cross-cutting features are implemented as plugins in `experimental/<feature>/` before v0.9.0-preview ships. Core has no feature-specific code; cross-cutting concerns are expressed exclusively through hook firing.

### Architectural goals

The plugin system optimizes for two properties:

1. **Security.** Default install ships only what v1.0 critical-path scope commits to. Plugins are registered via signed entry points, run in capability-restricted contexts, fail closed on errors, and are auditable from registration through every hook firing.
2. **Scalability.** Hook firing is O(1) per registered plugin per call. The registry is read-mostly after startup. Plugins declare async-safety in their manifest. The system supports thousands of registered plugins without coordination overhead at runtime.

These two properties are non-negotiable. Specific design choices below derive from them.

### The hook surface

Stigmem core fires named hooks at well-defined points in the protocol's request lifecycle. Plugins register handlers for hooks they care about. Core has no compile-time or import-time knowledge of any specific feature.

#### Fact assertion lifecycle

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `pre_assert_authorize` | AUTHZ | Before fact validation; capability and scope check | Voting (first deny wins) |
| `pre_assert_validate` | VALIDATE | After authorize; structural validation | Voting (first reject wins, with reason) |
| `pre_assert_transform` | TRANSFORM | After validate; enrichment (CID generation, derive_from, etc.) | Filter chain (fact in, fact out) |
| `post_assert_persist` | PERSIST | After successful storage | Fire-and-forget (no return) |
| `post_assert_propagate` | PERSIST | After persist; federation queue | Fire-and-forget |
| `post_assert_audit` | AUDIT | Always last after assert | Fire-and-forget |

#### Recall lifecycle

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `pre_recall_authorize` | AUTHZ | Before query parse; capability + tenant + scope | Voting |
| `pre_recall_rewrite` | TRANSFORM | After authorize; query transformation (as_of for time-travel, garden filter scope) | Filter chain (query in, query out) |
| `recall_filter` | FILTER | After search results returned; filter (tombstone removal, source-trust threshold, scope) | Filter chain (results in, results out) |
| `recall_rank` | RANK | After filter; ranking signal adjustment (source-trust, recency, derived-from boost) | Score-delta accumulation |
| `post_recall_audit` | AUDIT | Always last | Fire-and-forget |

#### Federation lifecycle

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `federation_peer_authenticate` | AUTHN | Inbound peer connection | Voting |
| `federation_inbound_validate` | VALIDATE | Inbound fact (HLC bounds, signature, scope) | Voting |
| `federation_inbound_filter` | FILTER | After validate; filter what peer is allowed to send | Filter chain |
| `federation_outbound_filter` | FILTER | Before send; filter what we send to peer (scope/tenant strip) | Filter chain |
| `federation_outbound_sign` | TRANSFORM | After filter; signature attachment | Filter chain |

#### Identity & auth

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `identity_resolve` | AUTHN | Per request; resolve identity from credentials | Filter chain (credentials in, identity out) |
| `tenant_resolve` | AUTHN | After identity_resolve; resolve tenant context (default: "system") | Filter chain (identity in, TenantContext out) |
| `capability_check` | AUTHZ | Per protected operation | Voting |

#### Lifecycle / maintenance

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `migration_register` | (startup) | Plugin registration; declare schema migrations | Filter chain (collect migrations) |
| `audit_emit` | AUDIT | Per audit event; plugins listen | Fire-and-forget |
| `decay_sweep_filter` | FILTER | Before decay sweep; exclude facts | Filter chain |
| `health_check` | OBSERVE | Periodic; report plugin health | Fire-and-forget (status reported) |

#### Configuration

| Hook | Band | When | Return semantics |
|---|---|---|---|
| `config_validate` | (startup) | Plugin registration; validate plugin config | Voting (registration aborts on reject) |

**Total: 22 hooks.** This is the *initial* surface; new hooks may be added via ADR-011 amendment with sign-off (two contributors or the founder alone, per ADR-001 §Contributor approval rule). Removing or changing the signature of an existing hook is a breaking change requiring a major version bump per ADR-013 deprecation policy.

### Hook composition order — bands

When multiple plugins register the same hook, they fire in order determined by **bands** plus FIFO within band:

| Band | Numeric value | Purpose |
|---|---|---|
| `AUTHN` | 10 | Identity resolution (must run before authz) |
| `AUTHZ` | 20 | Authorization checks |
| `VALIDATE` | 30 | Input/output validation |
| `TRANSFORM` | 40 | Input transformation (CIDs, query rewriting) |
| `FILTER` | 50 | Output filtering (tombstones, scope) |
| `RANK` | 60 | Output ranking adjustments |
| `PERSIST` | 70 | Write-side effects |
| `AUDIT` | 80 | Audit emission |
| `OBSERVE` | 90 | Metrics and logging (must not change behavior) |

Each hook in the surface above is bound to one band (see "Band" column). Plugins do not specify priority directly; their handler's band is determined by the hook they register for.

**Within a band**, plugins fire in order of plugin name (stable lexicographic). This is deterministic and operator-controllable: an operator can rename a plugin to control composition order if needed. Plugins MUST be designed to be order-independent within a band; relying on a specific peer plugin's behavior is a manifest declaration of dependency (which the registry validates as a topological constraint).

### Hook return semantics — typed protocol

Each hook category has typed semantics enforced by the registry:

**Voting hooks** (`pre_assert_authorize`, `pre_assert_validate`, federation auth/validate, `capability_check`):
- Each handler returns `Allow | Deny(reason: str)` or raises `RejectError(reason)`.
- Registry stops at first `Deny` or `RejectError`; subsequent handlers don't fire.
- If all return `Allow`, operation proceeds.
- Default (no plugin registered): `Allow` for optional checks, `Deny("not implemented")` for required checks.

**Filter chain hooks** (`pre_assert_transform`, `pre_recall_rewrite`, `recall_filter`, federation `inbound_filter` / `outbound_filter` / `outbound_sign`, `identity_resolve`, `tenant_resolve`, `decay_sweep_filter`, `migration_register`):
- Each handler receives the previous handler's output (or the initial input for the first handler).
- Returns the transformed value.
- Type signature is hook-specific and enforced.
- Default (no plugin registered): identity function (input passes through unchanged); for `tenant_resolve`, default returns `SystemTenant`.

**Score-delta hooks** (`recall_rank`):
- Each handler receives the current scored result list.
- Returns a `dict[fact_id, float_delta]` of adjustments.
- Registry sums all deltas and applies once.
- Default: empty deltas.

**Fire-and-forget hooks** (`post_assert_persist`, `post_assert_propagate`, `post_assert_audit`, `post_recall_audit`, `audit_emit`, `health_check`):
- Each handler executes independently.
- No return value; exceptions are logged and don't halt the operation.
- (Exception: in strict mode, exceptions in `post_assert_audit` and `audit_emit` are escalated — audit failures must not be silent.)

### Plugin lifecycle

#### Registration

Plugins register at process startup via Python `entry_points` (the same mechanism pytest plugins, setuptools, and the broader Python ecosystem use). The entry point group is `stigmem.plugins`.

**`pyproject.toml` example for a plugin:**

```toml
[project]
name = "stigmem-plugin-tombstones"
version = "1.0.0"
requires-python = ">=3.11"
dependencies = ["stigmem-core>=1.0.0,<2.0.0"]

[project.entry-points."stigmem.plugins"]
tombstones = "stigmem_plugin_tombstones:register"
```

The `register()` function returns a `PluginManifest`:

```python
def register(context: PluginContext) -> PluginManifest:
    return PluginManifest(
        name="tombstones",
        version="1.0.0",
        requires_stigmem=">=1.0.0,<2.0.0",
        capabilities={"facts.read", "facts.write", "audit.emit"},
        async_safe=True,
        hooks={
            "post_assert_persist": handle_assert_for_tombstone_propagation,
            "recall_filter": filter_tombstoned_facts,
            "federation_inbound_validate": validate_tombstone_signature,
            "migration_register": declare_tombstone_migrations,
        },
        config_schema=TombstonesConfig,  # Pydantic model
        depends_on={"federation"},  # other plugin names this depends on
    )
```

#### Registration validation

Core validates each plugin at registration. Failure to validate aborts process startup with a clear error message. Validation checks:

1. **Manifest schema.** Manifest is well-formed.
2. **Stigmem version compatibility.** `requires_stigmem` is satisfied by current stigmem version.
3. **Hook signatures.** Each registered handler matches the expected signature for its hook (return type, argument types).
4. **Capability declaration.** Plugin's declared `capabilities` are in the allowlist (no escalation by registration).
5. **Dependency resolution.** Declared `depends_on` plugins are also registered; no cycles.
6. **Configuration validity.** `config_validate` hook fires; any plugin's `config_schema` validates against actual config (env vars / pyproject section).
7. **Signature validation (production).** In production mode (default), plugin's distribution must be cryptographically signed by a trusted key. Sigstore signatures verified at registration. In development mode (explicit env var), signing is skipped with loud startup warning.

#### Health monitoring

Plugins MAY implement `health_check`. Core polls plugin health every 60 seconds (configurable). Unhealthy plugins:
- Are logged with a warning.
- Are NOT auto-disabled. Operator action only — automatic disabling can mask real problems.
- If a plugin fails registration after restart, that's the operator's signal.

#### Deregistration

Only at process shutdown. No hot-unloading. If an operator wants to remove a plugin, they uninstall the package and restart the process. Hot-unloading introduces consistency hazards (in-flight requests) that aren't worth the complexity for v1.0.

### Plugin trust and security model

The plugin system follows defense-in-depth principles. The threat model: a malicious or buggy plugin must not be able to compromise data integrity, exfiltrate data beyond its declared capabilities, or escalate the privileges of other plugins.

#### Capability-restricted contexts

Plugins receive a `PluginContext` at registration that contains restricted handles to core APIs. Capabilities are declared in the manifest and enforced at API call time:

```python
class PluginContext:
    def get_facts_reader(self) -> FactsReader:
        """Available if 'facts.read' capability declared."""
        # raises CapabilityError otherwise

    def get_audit_emitter(self) -> AuditEmitter:
        """Available if 'audit.emit' capability declared."""

    def get_federation_outbound(self) -> FederationOutbound:
        """Available if 'federation.write' capability declared."""

    # ... typed accessors per capability
```

Capability values are an enumerated allowlist. New capabilities require ADR-011 amendment.

The well-known capability set (initial):
- `facts.read`, `facts.write`
- `recall.read`, `recall.write` (separate because the recall path has different reader semantics)
- `audit.emit`, `audit.read`
- `federation.read`, `federation.write`
- `identity.read`, `tenant.read`, `tenant.write`
- `config.read`
- `network.outbound` (most plugins do not get this; only plugins like cloud embedding adapters)

A plugin's manifest declares capabilities at registration. Any attempt to access a capability not declared raises `CapabilityError` at the API call site.

#### Code signing (production default)

In production mode, plugins must be cryptographically signed via Sigstore (or equivalent transparency-log-backed signing). At registration:

1. Plugin's distribution is hashed.
2. Signature is verified against a transparency log entry.
3. Signing identity is checked against the operator's trusted-publisher list (defaults to Eidetic Labs and known-good plugin authors).
4. Failure halts registration.

Operators can disable signing for development with `STIGMEM_PLUGIN_SIGNING_REQUIRED=false`. This emits a loud startup warning that's logged at every request until the env var is removed.

#### Manifest declaration audit trail

Plugin registration is itself an audit event. The audit log records:
- Plugin name, version, dependencies.
- Declared capabilities.
- Signing identity (production) or "UNSIGNED" (development).
- Stigmem version at the time of registration.

Operators can audit "what plugins are running and what can they do" via `stigmem plugins describe`.

#### Failure mode: fail-closed

Plugins that fail (registration error, exception in a non-fire-and-forget hook, capability violation) abort the operation they were participating in. Plugins NEVER silently no-op on error. Errors propagate as `PluginExecutionError` with traceback to the calling operation.

#### No introspection

Plugins cannot:
- List other registered plugins.
- Read other plugins' configuration.
- Modify other plugins' state.

This is enforced by the `PluginContext` not exposing such APIs. Information leakage between plugins is structurally impossible.

#### Async-safety declaration

Each plugin declares `async_safe: bool` in its manifest. Stigmem's runtime is async-first; plugins that aren't async-safe run in a thread pool with documented overhead. This forces plugin authors to make a conscious choice and lets operators see which plugins block the event loop.

### Plugin scalability

The architecture commits to specific scalability properties:

#### Hook firing performance

The registry is a `dict[hook_name, list[HandlerEntry]]` populated at startup. Per-call overhead:
- Lookup: O(1).
- Fire: O(N) where N = number of registered handlers for that hook.
- For 100 registered plugins each with one handler per hook on average, N is typically 1-3 per hook. Effective overhead: tens of microseconds per hook firing.

Hooks must NOT do expensive setup at fire time. Setup happens at registration. If a plugin needs configured state, it captures a closure at registration.

#### Read-mostly registry

After process startup, the registry is read-only. No locks needed for reads. Plugin registration / deregistration only at process boundaries.

#### Backpressure and rate limiting

The plugin system itself does NOT impose rate limits on hook firing. Rate limiting belongs in the protocol layer (per ADR-009 / R-23). Plugins that want to rate-limit their work do so via their own internal mechanisms (e.g., cap on outbound network calls).

#### Concurrency model

- Async-safe plugins run inline in the event loop.
- Non-async-safe plugins run in a `ThreadPoolExecutor` with a configurable worker count (default: 4).
- A plugin that mixes both should declare `async_safe=false`; partial async-safety is a documentation hazard.

#### Memory footprint

- Each registered plugin: typically 100KB-1MB depending on what it imports.
- Stigmem core targets supporting 50+ registered plugins without memory pressure.
- Plugins are encouraged but not required to lazy-import their dependencies.

### Configuration model

Per-plugin configuration via two mechanisms (operators choose):

**Environment variables:**
- `STIGMEM_PLUGIN_<NAME>_<KEY>=<value>`
- e.g., `STIGMEM_PLUGIN_TOMBSTONES_RETENTION_DAYS=90`

**Declarative pyproject.toml section:**
```toml
[tool.stigmem.plugins.tombstones]
retention_days = 90
sign_outgoing = true
```

Both are read at startup and fed into the plugin's `config_schema` (a Pydantic model). The plugin's `config_validate` hook fires on registration; rejection aborts startup.

Operators discover plugin config via:
```
$ stigmem plugins describe tombstones
Plugin: tombstones
Version: 1.0.0
Config:
  retention_days: int (default: 90, min: 1, max: 3650)
  sign_outgoing: bool (default: true)
Capabilities: facts.read, facts.write, audit.emit
Hooks: post_assert_persist, recall_filter, federation_inbound_validate, migration_register
```

### Testing infrastructure

#### Test plugin registry

Tests use a `TestPluginRegistry` that mounts plugins for the test's duration:

```python
def test_recall_with_tombstones():
    with stigmem_plugins([TombstonesPlugin, TenantsPlugin]):
        # registry contains exactly these two plugins
        result = recall(query)
        assert tombstoned_fact not in result
```

#### Hook protocol tests

Tests can fire hooks against a controlled registry without going through full request paths:

```python
def test_recall_filter_composition_order():
    registry = TestRegistry()
    registry.register("recall_filter", first_filter, band="FILTER", priority=1)
    registry.register("recall_filter", second_filter, band="FILTER", priority=2)
    result = registry.fire("recall_filter", initial_results)
    # Verify ordering and composition
```

#### Composition tests

Each cross-cutting feature (now a plugin) ships with its own composition tests verifying:
- Hook ordering is deterministic.
- Capability violations are caught.
- Failure mode is fail-closed.
- Configuration validation rejects bad input.

#### Conformance integration

The v1.0 conformance vectors fire against a default install (no plugins) to verify the no-plugin baseline. Each plugin ships its own conformance vectors that fire against the registry with that plugin loaded.

### Default behavior — no plugins registered

When no plugin is registered for a hook:
- **AUTHN/AUTHZ hooks (voting):** default to `Allow` for optional checks, `Deny("not implemented")` for required ones. `tenant_resolve` defaults to `SystemTenant`. `identity_resolve` defaults are based on configured auth mode (system identity for unauthenticated, configured identity for API-key paths).
- **VALIDATE hooks:** structural validation runs in core (always-on); plugin VALIDATE hooks are layered additions.
- **TRANSFORM hooks:** identity function — input passes through unchanged.
- **FILTER hooks:** identity function — full result set returned.
- **RANK hooks:** zero deltas — base scoring applies.
- **PERSIST/AUDIT hooks:** core's built-in audit and persistence run; plugin hooks are layered additions.

This is the architectural promise of C1: **default install matches v1.0 critical-path scope exactly.** Single-tenant, no tombstones, no time-travel, no CIDs, no source attestation, no advanced ACL, no lazy instruction discovery — because no plugins for those concerns are registered.

### Per-feature plugin manifests (Phase A scope)

Seven plugins implemented in Phase A:

| Plugin | Replaces concept | Hooks registered | Estimated effort |
|---|---|---|---|
| `stigmem-plugin-lazy-instruction-discovery` | §21 | `pre_recall_rewrite`, `recall_filter` (lazy boot), `migration_register` | 5-7 days |
| `stigmem-plugin-cids` | §25 | `pre_assert_transform` (generate CID), `federation_inbound_validate` (verify CID), `migration_register` | 4-5 days |
| `stigmem-plugin-time-travel` | §24 | `pre_recall_authorize` (require capability), `pre_recall_rewrite` (as_of rewriting), `migration_register` | 5-7 days |
| `stigmem-plugin-tombstones` | §23 | `recall_filter`, `federation_inbound_validate`, `post_assert_propagate` (RTBF), `migration_register` | 7-10 days |
| `stigmem-plugin-memory-garden-acl` | §17 advanced | `pre_assert_authorize`, `pre_recall_authorize`, `recall_filter` | 5-7 days |
| `stigmem-plugin-source-attestation` | §18 | `pre_assert_validate`, `recall_rank` (source-trust signal), `federation_inbound_validate` | 5-7 days |
| `stigmem-plugin-multi-tenant` | multi-tenant | `tenant_resolve`, `pre_assert_authorize`, `pre_recall_authorize`, `recall_filter`, `federation_outbound_filter`, `migration_register` | 14-21 days |

Multi-tenant remains the largest plugin (most hooks, hardest semantics). Default install: no multi-tenant plugin → `tenant_resolve` returns `SystemTenant` → core is single-tenant.

### Versioning and compatibility

- Plugins declare `requires_stigmem` SemVer range. Core checks at registration.
- Stigmem MAJOR version bumps may require plugin re-release; plugins should test against `>=X.0.0,<X+1.0.0`.
- Hook signatures are part of the stable API per ADR-013 deprecation policy. Changing a hook signature requires major version bump.
- New hooks are additive (MINOR bumps).
- Plugins can be developed and shipped independently of core releases as long as they stay within their declared `requires_stigmem` range.

## Alternatives considered

**1. Option C2 (thin shims).** Rejected (was the prior decision). Reasons C1 wins:
- Same "do it once" argument that rejected C3-then-C2 also rejects C2-then-C1.
- C2's named integration points (e.g., `process_recall_tombstones()`) embed feature-specific concept names in core. C1's generic hooks (e.g., `recall_filter`) don't. C1 is more scope-honest.
- C2's reintroduction story under ADR-008 still requires architectural changes when a feature graduates. C1's reintroduction is a label change — the plugin stays a plugin, it's just trusted to default-on for new installs.
- External contributor story: C2 requires core PRs to add new integration points; C1 supports new features as plugin packages without core changes.

**2. Option C3 (feature flags only).** Rejected. Same reasons as in the prior version of this ADR: scope contract leak, security surface includes everything regardless of enablement, no path to graduation that doesn't involve refactor.

**3. Direct plugin loading (no registry).** Rejected. Without a registry, plugins are discovered by import order. This makes hook composition order implicit and fragile, prevents capability-restricted contexts (no central enforcement point), and makes operator audit ("what's running") expensive.

**4. Plugin sandboxing via subprocess isolation.** Rejected for v1.0. Subprocess isolation is the strongest security model (a malicious plugin can't compromise core's memory) but adds significant per-call overhead and complicates the hook return semantics (serialization across process boundaries). Reconsider for v2.0 if the plugin ecosystem grows or threat model changes.

**5. WebAssembly-based plugin model.** Rejected for v1.0. WASM-based plugins (like Envoy's Wasm filters or Spin's component model) provide language-agnostic plugins with capability-based security. Genuinely interesting for the long term but the tooling, debug story, and ecosystem are still maturing for Python-first projects. Defer to a future ADR.

**6. Hook-firing order via topological dependencies only (no bands).** Considered. Bands + FIFO is simpler to reason about and matches real-world usage patterns (Apache, pytest, etc.). Plugins that need explicit ordering relative to a peer can declare dependencies, which the registry uses to validate (no cycles); ordering within a band stays FIFO.

**7. No code signing in v1.0; trust on first install.** Rejected. Plugin signing is the difference between a plugin ecosystem that's hardenable and one that isn't. Doing it right at v1.0 is much cheaper than retrofitting later.

## Consequences

### What gets easier

- **Default install matches scope contract exactly.** The architecture itself enforces the v1.0 scope boundary; there's no risk of feature creep into core.
- **Reintroduction is a label change.** When a feature graduates from experimental per ADR-008, the plugin stays a plugin; only its trust tier changes. No core refactor needed.
- **Security surface is bounded by capabilities, not feature counts.** Audit answers "what can plugin X do?" via the manifest, not by reading source.
- **External contributors can write plugins.** Once the hook surface is stable, third-party plugins are first-class. No core PR needed to add a feature.
- **Failure mode is uniform.** All plugins fail-closed via the same mechanism. Operators have one place to look when something breaks.
- **Auditability is built in.** Plugin registration is an audit event; capability declarations are explicit; signing identifies trusted publishers.
- **Versioning is consistent.** Plugins follow SemVer with stigmem-version compatibility ranges, integrating cleanly with ADR-012's `Stigmem-Version` header model and ADR-013's deprecation policy.

### What gets harder

- **Phase A timeline grows substantially.** Plugin infrastructure is ~2-3 weeks before any feature extracts. Per-feature plugin work is similar to C2 extraction work (~5-7 weeks for the seven features). Total Phase A extension: roughly 9-12 weeks. v0.9.0-preview ships later than under C2 or C3.
- **Architectural decisions are sticky.** Hook surface changes are breaking. The strawman in this ADR commits us to a specific surface; getting it wrong is expensive.
- **Plugin authors face higher bar.** Writing a plugin requires understanding the hook surface, capability model, signing requirements. Documentation has to compensate (the plugin author guide is part of Phase A docs work).
- **Test infrastructure investment.** TestPluginRegistry, hook composition tests, conformance integration — all real engineering work that pays off later but takes time upfront.
- **Operator complexity increases.** Operators have a new concept (plugins) to understand. CLI tools (`stigmem plugins list`, `stigmem plugins describe`) help; documentation and operator guides have to make this approachable.

### New risks

- **R-PLUG-1: hook surface design wrong.** The strawman in this ADR is a best guess. If a hook is missing or has wrong semantics, plugins can't express what they need. Mitigation: hook surface is an ADR-011 amendment; new hooks are additive (MINOR); existing hooks can be deprecated per ADR-013. The first six plugin implementations are the test — if they all map cleanly to the surface, the design is sound; if they require workarounds, the surface needs revision before multi-tenant lands.
- **R-PLUG-2: registry overhead at runtime.** Hook firing on the request hot path could become a bottleneck. Mitigation: registry is a flat dict-of-lists; no dynamic lookups; benchmark per-hook overhead in CI; budget: under 10μs per hook firing.
- **R-PLUG-3: plugin signing infrastructure delays.** Sigstore integration adds dependency on a Sigstore-compatible signing pipeline. Mitigation: development mode allows unsigned plugins (with loud warning); production signing can land in v0.9.x if it's not ready by v0.9.0-preview tag. The architecture is designed to accept this gracefully.
- **R-PLUG-4: capability set drift.** New plugins request new capabilities; the allowlist grows. Mitigation: capability additions require ADR-011 amendment; the discipline of adding each is the gate.
- **R-PLUG-5: security regression in a plugin compromises operator.** A bug in tombstones plugin (for example) causes data loss in operators who installed it. Mitigation: signing identifies the responsible publisher; audit log shows registration provenance; capability boundaries limit blast radius (a buggy `recall_filter` can't write to the audit log if it didn't declare `audit.emit`).
- **R-PLUG-6: plugin evolution drives core surface churn.** Plugins demand new hooks; the surface grows. Mitigation: hook additions are additive (no breaking changes); ADR amendment process is the gate; periodic review of hook surface bloat at major version boundaries.

### Net effect on the project

- **v1.0 ships with a tight, auditable core and a coherent plugin architecture.** Adopters know exactly what default install does. Operators choose their security/feature tradeoff explicitly via plugin install.
- **The `experimental/` directory becomes a directory of plugin packages.** Each is independently versioned, releaseable, and deprecatable. ADR-008 reintroduction gates apply to plugins; graduation is about trust, not architecture.
- **The architecture is recognizably a "serious infrastructure project" pattern.** It maps to PostgreSQL extensions, pytest plugins, Envoy filters, and similar systems that the federated infrastructure category respects.

## Implementation plan

### Phase A: plugin infrastructure (weeks 1-3 of extraction work)

Order matters. Infrastructure first, then the seven plugins.

#### Phase A.1: Hook protocol and registry (~1 week)

- [ ] Implement `HookRegistry` with band-based composition order.
- [ ] Implement `HookHandler` typed protocols (voting, filter chain, score-delta, fire-and-forget).
- [ ] Implement `PluginContext` and capability-restricted accessors.
- [ ] Implement `PluginManifest` schema and validation.
- [ ] Add hook firing in core at all 22 named locations. Until plugins exist, all hooks fire with empty handler lists (defaults).
- [ ] Verify: empty registry produces single-tenant, no-cross-cutting-features behavior identical to v1.0 critical-path scope.
- [ ] Benchmark hook firing overhead; budget enforcement in CI (<10μs per hook).

#### Phase A.2: Lifecycle, validation, signing (~1 week)

- [ ] Plugin discovery via `entry_points`.
- [ ] Manifest validation at registration; failure aborts startup.
- [ ] Capability allowlist enforcement.
- [ ] Dependency resolution (depends_on); cycle detection.
- [ ] Sigstore-based signing in production mode; dev-mode override with warning.
- [ ] Plugin registration audit events.
- [ ] Health-check polling and reporting.
- [ ] CLI: `stigmem plugins list`, `stigmem plugins describe`.

#### Phase A.3: Testing infrastructure (~3-5 days)

- [ ] `TestPluginRegistry` for test mounting.
- [ ] `pytest` fixture: `stigmem_plugins([...])`.
- [ ] Hook protocol unit tests.
- [ ] Composition order tests.
- [ ] Capability violation tests (negative testing).
- [ ] Failure-mode tests (fail-closed verification).

#### Phase A.4: Documentation (~3-5 days)

- [ ] Plugin author guide in `docs/Build/Plugins/`.
- [ ] Hook reference in `docs/Reference/Plugin-API/`.
- [ ] Capability reference.
- [ ] Operator guide for plugin management in `docs/Operate/Plugins/`.
- [ ] Migration guide for any operators currently using v1.0 features that become plugins (mostly applies to internal testers since v1.0 was retracted).

### Phase A: per-feature plugin implementations (weeks 4-12)

Each plugin is its own three-PR cycle:

1. **Pre-implementation analysis PR.** Document the plugin's hook usage, capability requirements, and configuration. Validate the hook surface supports what the plugin needs; if it doesn't, file an ADR-011 amendment first.
2. **Implementation PR.** Implement the plugin in `experimental/<feature>/`. Includes plugin code, tests, manifest, docs.
3. **Validation PR.** Conformance vectors with the plugin loaded; integration tests; signed release artifact.

Per-feature ordering:

- **Week 4-5: lazy-instruction-discovery** (priority 1; couples to ADR-003).
- **Week 5-6: cids** (validates the plugin pattern on a tightly-bounded module).
- **Week 6-7: time-travel** (mid-difficulty; tests query rewriting hook semantics).
- **Week 7-9: tombstones** (largest non-multi-tenant; tests recall_filter under load).
- **Week 9-10: memory-garden-acl** (tests authz hooks).
- **Week 10-11: source-attestation** (tests rank hook).
- **Week 11-12: multi-tenant** (most complex; capability model gets its hardest test here).

### Phase A exit (v0.9.0-preview ships)

- [ ] All seven plugins implemented, tested, signed, released.
- [ ] Default install (no plugins) produces v1.0 critical-path behavior.
- [ ] Conformance vectors pass against default install AND against the full plugin set.
- [ ] Plugin author docs published; first plugin contributors can self-serve.
- [ ] Operator docs explain plugin management and trust posture.
- [ ] No core code references any specific feature by name (other than as test scaffolding).

### Post-Phase-A: stewardship

The hook surface is reviewed at every major release for:
- Hook deprecations (per ADR-013).
- New hooks (additive; ADR-011 amendment).
- Capability evolution.

Phase B (capability redesign, federation hardening, OpenClaw rewrite, operator soak) operates against the post-extraction codebase. The plugin architecture provides the substrate for Phase B work; capability redesign per ADR-003 likely adds new authn/authz hooks for the redesigned semantics.

## Amendment process

This ADR commits to:
1. C1 plugin architecture as the cross-cutting strategy.
2. The 22-hook surface (with bands).
3. The capability model with declared allowlist.
4. The signing/trust model (Sigstore in production, dev override with warning).
5. The plugin lifecycle (entry-point discovery, registration validation, no hot-unload).
6. The default-install-matches-scope-contract guarantee.

Changes require ADR-011 amendment with sign-off (two contributors or the founder alone, per ADR-001 §Contributor approval rule). Common amendment cases:

- Adding a new hook (additive; MINOR core version bump).
- Adding a new capability to the allowlist.
- Changing a hook signature (breaking; MAJOR core version bump per ADR-013).
- Adding plugin sandboxing (subprocess isolation, WASM-based, etc.) — would supersede the registration-only trust model.
- Promoting a plugin's default-on status (would also amend ADR-008 reintroduction gates if applicable).

---

*Accepted by: @offbyonce (founder), 2026-05-07. Per ADR-001 §Contributor approval rule (founder solo-approval; second contributor sign-off welcome but not required).*