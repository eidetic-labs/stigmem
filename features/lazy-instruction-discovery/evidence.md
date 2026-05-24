# Lazy Instruction Discovery Evidence

## Implementation Paths

| Path | Purpose |
| --- | --- |
| `experimental/lazy-instruction-discovery/pyproject.toml` | Plugin package metadata and entry point. |
| `experimental/lazy-instruction-discovery/src/stigmem_plugin_lazy_instruction_discovery/manifest.py` | Plugin manifest, capabilities, hooks, and routes. |
| `experimental/lazy-instruction-discovery/src/stigmem_plugin_lazy_instruction_discovery/config.py` | Plugin configuration gates. |
| `experimental/lazy-instruction-discovery/src/stigmem_plugin_lazy_instruction_discovery/routes.py` | Lazy-instruction API routes. |
| `experimental/lazy-instruction-discovery/boot-stubs/` | Boot-stub examples. |

## Tests and Validators

| Check | Path or command | Coverage |
| --- | --- | --- |
| Plugin scaffold | `node/tests/plugins/test_lazy_instruction_plugin_scaffold.py` | Entry point, manifest, config, routes, and registration. |
| Plugin integration | `node/tests/plugins/test_lazy_instruction_plugin_integration.py` | Plugin-loaded route behavior. |
| Publication contract | `node/tests/plugins/test_security_plugin_publication_contract.py` | Package metadata, entry point, build metadata, README presence, and feature status publication-state checks. |
| Instruction channel tests | `node/tests/instruction/test_phase10_instruction.py` | Instruction-typed fact handling and recall channel behavior. |
| Migration lifecycle tests | `node/tests/lifecycle/test_instruction_migrate_b2.py` | Instruction migration behavior. |
| Fast gate | `bash scripts/check.sh python` | Python lint, type, tests, and security bundle. |

## Coverage Gaps

- Full adversarial vectors for instruction promotion/admission are incomplete.
- External operator soak evidence is not recorded.
- Supported-adapter conformance evidence remains incomplete.
