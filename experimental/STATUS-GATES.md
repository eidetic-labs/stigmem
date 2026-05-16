# Experimental Feature Status Gates

Per [ADR-008](../docs/adr/008-experimental-gates.md), every experimental feature returns to the supported surface only after completing these gates:

| Gate | Description | Default artifact |
|---|---|---|
| 1 | Threat-model delta | `spec/security/deltas/<feature>-threat-model.md` |
| 2 | ADR | `docs/adr/NNN-<feature>.md` |
| 3 | Conformance vectors | `data/conformance/<feature>/` |
| 4 | 30-day external operator soak | `LOG.md` entry |
| 5 | Documentation parity | Learn / Build / Operate / Secure pages |

Feature-local `STATUS.md` files carry only the feature-specific state. This shared page owns the common gate language to avoid 30-plus copies drifting apart.
