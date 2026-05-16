# PR 4f Source Attestation Extraction Analysis

Date: 2026-05-16

Parent: #340

## Intent

PR 4f extracts source-attestation behavior into the opt-in experimental
`stigmem-plugin-source-attestation` source package while preserving the default
install critical path. Default installs should keep accepting ordinary fact
writes without source-attestation enforcement, source-trust rank boosts, or
federation attestation-chain validation unless the plugin is registered and
explicitly enabled.

## Current Surface

| Surface | Files | Current behavior | PR 4f boundary |
|---|---|---|---|
| Source mismatch check | `node/src/stigmem_node/routes/facts/common.py`, `node/src/stigmem_node/routes/_facts_assert.py` | `_check_source_attestation` compares normalized `source` to `identity.entity_uri`; mode `enforce` rejects, `warn` accepts with `attested=false`, `off` stores `attested=null`. | Plugin-owned advanced source-attestation behavior. Route should keep stable request/response fields, but enforcement/warn decisions should be gated behind plugin registration/config. |
| Ed25519 assertion token | `node/src/stigmem_node/models/facts.py`, `node/src/stigmem_node/routes/_facts_assert.py`, `node/src/stigmem_node/routes/agent_keys.py` | `AssertRequest.attestation` carries an optional signature; `_verify_or_require_attestation` validates it when present or when `STIGMEM_ATTESTATION_REQUIRED=true`; agent-key CRUD stores registered public keys. | Split carefully. The data shape and agent-key management may stay baseline identity infrastructure until plugin launch owns the policy. The requirement/verification policy should move behind `pre_assert_validate` or a plugin gate. |
| Fact/audit data model | `node/src/stigmem_node/models/facts.py`, migrations, `routes/audit.py`, `audit_event.py`, admin/static views | Facts expose `attested`, `attested_key_id`, and source-trust/audit fields; audit routes can filter/enrich attested key references. | Keep compatibility columns and audit read surfaces core unless a later migration plan proves removal is safe. Plugin should populate or leave them inert; default installs must not require attestation. |
| Query filters | `node/src/stigmem_node/routes/facts/query.py`, OpenAPI/docs generated from models/routes | `attested` query parameter filters facts by source-attestation result. | Keep the parameter for compatibility in PR 4f, but default installs should not create new attestation decisions beyond inert/null behavior. A later docs closeout can mark it experimental/plugin-populated. |
| Source trust computation | `node/src/stigmem_node/source_trust.py`, `trust_rules.py`, quarantine/graph/card callers | Computes trust from identity strength, peer history, scope authority, and `settings.source_attestation_mode`; feeds effective confidence and recall ranking. | Split source-attestation-specific score input from baseline trust/quarantine behavior. The `trust_weight_attestation_mode` contribution belongs to the plugin; generic operator trust rules and quarantine mechanics can remain core until their own extraction decision. |
| Recall ranking | `node/src/stigmem_node/routes/recall/ranking.py`, `node/src/stigmem_node/routes/recall/as_of.py`, `node/src/stigmem_node/recall_pipeline.py`, `routes/facts/query.py` | Recall pipeline computes source trust directly, then query path also fires `recall_rank` score deltas. | Move source-attestation rank contribution to `recall_rank`; default ranking should not import or compute source-attestation-specific boosts when plugin is absent. Time-travel `as_of` should not gain plugin behavior until PR 4f validation covers it or explicitly defers it. |
| Federation inbound validation | `node/src/stigmem_node/routes/federation/replication.py` | Push paths already fire `federation_inbound_validate`; core also enforces scope/capability/source non-forgery checks. | Keep core source non-forgery and capability checks. Plugin should own attestation-chain validation through `federation_inbound_validate`. |
| Well-known advertisement | `node/src/stigmem_node/routes/wellknown.py`, `settings.py` | Always advertises `source_attestation` from settings. | Should reflect plugin state after gating: default install should advertise off/inactive or omit advanced mode; plugin-loaded mode can advertise configured source-attestation posture. |

## Hook Plan

| Hook | PR 4f use |
|---|---|
| `pre_assert_validate` | Validate source-attestation policy before persistence. This covers bearer/source mismatch checks and, if kept policy-owned, Ed25519 assertion-token requirements. |
| `recall_rank` | Add source-attestation/source-trust score deltas after baseline recall filtering. This avoids default installs importing plugin-owned score inputs. |
| `federation_inbound_validate` | Validate inbound attestation evidence after core scope/capability/source non-forgery checks and before ingest. |

## Core Baseline

Keep these in core for PR 4f:

- `source` as a required fact field and existing normalization/aliasing.
- Agent-key CRUD and audit read models unless the implementation PR proves a
  safe compatibility-preserving move.
- Fact columns and response fields (`attested`, `attested_key_id`,
  `source_trust`) as compatibility storage/read surfaces.
- Federation scope authorization, capability-token validation, and source
  non-forgery checks.
- Operator trust rules and quarantine routing not explicitly tied to
  source-attestation mode.

## Plugin-Owned Behavior

Move or gate these behind `stigmem-plugin-source-attestation` registration and
explicit configuration:

- Source mismatch enforce/warn/off decisions.
- `STIGMEM_ATTESTATION_REQUIRED` policy and Ed25519 assertion-token enforcement
  if the implementation keeps agent-key verification as source-attestation
  policy rather than baseline identity infrastructure.
- Source-attestation contribution to source-trust scoring and recall ranking.
- Federation inbound attestation-chain validation.
- Well-known source-attestation advertisement beyond inert/off default state.

## Risks And Follow-Ups

- The current `source_trust.py` module mixes source-attestation, federation
  trust, quarantine history, and operator trust rules. PR 4f should avoid
  moving the whole module blindly.
- `attested` query filtering is already public API. Removing it would be a
  breaking change; PR 4f should make it inert/plugin-populated instead.
- `routes/agent_keys.py` names itself source-attestation infrastructure, but
  agent keys are also useful for broader identity and audit. Treat policy as
  movable before treating the whole route as movable.
- Generated OpenAPI files may need regeneration only if route/model signatures
  change. Boundary/scaffold work should not alter generated API artifacts.
- Local Stigmem facts could not be written during this analysis because
  `http://127.0.0.1:18765` refused connections.

## Implementation Slices

1. #342 scaffolds `experimental/source-attestation` with manifest, config, hook
   placeholders, and registration/order tests.
2. #343 gates default-install source-attestation behavior behind plugin
   registration/config while preserving baseline source and audit surfaces.
3. #344 validates plugin-loaded behavior and deterministic hook ordering.
4. #345 closes public and Internal-Comms docs once implementation/validation
   land.
