# Muninn — Federated Knowledge Fabric + Intent Protocol

> **Status: v0.2 draft — actively seeking design partners for the federation section.**

Muninn is an open specification for a federated knowledge fabric: a shared, persistent layer where AI agents and humans can write facts, query relationships, and hand off work — across tools, platforms, and organizations.

## The problem

Every agent, every human, and every company maintains its own private memory. Facts decay silently, contradict each other across contexts, carry no provenance, and cannot travel with the entity they describe. When you switch tools, change agents, or cross an org boundary, context evaporates.

Muninn is the missing substrate: an open, federated knowledge fabric that any agent or human can write facts into and query against, plus a typed intent/protocol layer so agents can express goals, hand off work, and defer to each other without designing bespoke handshake protocols every time.

## Core concepts

### Atomic facts

Every piece of knowledge is an atomic, immutable fact:

```
(entity, relation, value, source, timestamp, confidence, scope)
```

Facts are **immutable** — updates create new facts. **Contradictions are surfaced**, not silently overwritten. **Provenance is first-class** — every fact carries its source and timestamp; queries return them unchanged.

### Scopes and federation

Facts have four scopes: `local`, `team`, `company`, `public`. Only `public` facts federate across nodes. Federation uses a signed peer declaration model (like email's MX/SMTP trust) — two nodes federate when both operators agree.

### Intent envelopes

Beyond facts (world state), Muninn defines a typed **intent envelope** — a structured message from one actor to another expressing a desired transition, with constraints, soft preferences, deference rules, and handoff payloads.

## What Muninn is not

Muninn does not replace company orchestration platforms, agent runtimes, or tool protocols. It is a shared cognitive layer that sits above them — readable and writable by anything that speaks JSON over HTTP.

## Spec

- [`spec/loom-spec-v0.2.md`](spec/loom-spec-v0.2.md) — current working draft

## Prototype

A minimal reference implementation lives in [`prototype/`](prototype/). It implements the v0.1 wire format (assert/query facts, no federation yet).

```bash
cd prototype
pip install -r requirements.txt
python main.py
```

See [`prototype/seed_memory.py`](prototype/seed_memory.py) for example fact writes.

## Current status

| Area | Status |
|---|---|
| Core fact shape (§2) | Stable draft |
| Fact semantics: provenance, decay, contradiction (§3) | Stable draft |
| Intent envelope (§4) | Draft — feedback wanted |
| Wire format v0.1 HTTP/JSON (§5) | Implemented in prototype |
| Federation handshake (§6) | Sketch only — **co-authors wanted** |
| Auth / identity (Phase 2) | Not yet specified |
| Namespace registry (`loom:`, `rel:`, `memory:`) | Open question |

## Design partner track

We are looking for **3 design partners** to co-author the federation section (v0.3). Ideal design partners have built persistent memory, knowledge graphs, or agent-to-agent coordination systems and have strong opinions about what good looks like.

Co-authoring the federation section means: a 30-minute interview, async spec review on a PR, and your name on the spec.

**Interested?** Open an issue tagged [`design-partner`](../../labels/design-partner) or email the spec maintainer.

## How to contribute

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full RFC process.

Short version:
1. Open an issue using the [RFC template](.github/ISSUE_TEMPLATE/rfc.yml)
2. Discuss; iterate on the issue thread
3. Submit a PR against `spec/loom-spec-v0.2.md` (or the active version)
4. Spec changes merge with ≥2 approvals from active contributors

## License

Apache-2.0. See [LICENSE](LICENSE).
