# RTBF Tombstones Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/tombstones/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/manifest.py` | Plugin manifest, capabilities, hooks, and migration registration. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/config.py` | Plugin configuration gates. |
| `experimental/tombstones/src/stigmem_plugin_tombstones/handlers.py` | Hook handlers for recall filtering, federation validation, propagation, and migrations. |
| `node/src/stigmem_node/lifecycle/tombstone_gate.py` | Runtime gate that requires plugin registration and explicit operator enablement before tombstone filters apply. |
| `node/src/stigmem_node/lifecycle/tombstones.py` | Tombstone storage, revocation, inbound application, and audit emission for local and federated tombstone decisions. |
| `node/src/stigmem_node/routes/_federation_impl.py` | Inbound federation authentication, signer authority validation, signature verification, and rejection audit emission. |
| `node/src/stigmem_node/routes/facts/common.py` | Shared fact-route tombstone filter application point. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_tombstone_plugin_scaffold.py` | Entry point, manifest, config, route gates, filter gates, hooks, and migration declaration. |
| Plugin gating | `node/tests/plugins/test_tombstone_plugin_gating.py` | Default-install gating, route registration, filter enablement, and plugin-loaded behavior. |
| Publication contract | `node/tests/plugins/test_security_plugin_publication_contract.py` | Package metadata, entry point, build metadata, README presence, and feature status publication-state checks. |
| Tombstone behavior | `node/tests/tombstones/` | Filtering, provenance, admin behavior, tombstone route behavior, selective revocation recovery, legal-hold silence, side-channel checks, signer authority, forged signature rejection, and audit events. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- External operator soak evidence is not recorded.
- Legal-hold and revocation recovery runbooks remain open.
- Federation propagation adversarial evidence is not sufficient for
  graduation.
