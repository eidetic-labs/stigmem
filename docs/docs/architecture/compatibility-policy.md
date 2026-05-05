---
id: compatibility-policy
title: Compatibility Policy
description: Compatibility perimeter, support window, and CI obligations for public Stigmem surfaces.
---

# Compatibility Policy

This repository uses three compatibility tiers instead of applying one uniform promise to every package.

## Compatibility perimeter

The formal compatibility perimeter is:

- the HTTP API under `/v1`
- the generated OpenAPI document in `docs/openapi/stigmem.json`
- the versioned conformance vectors in `data/conformance/`
- the Python, TypeScript, and Go SDKs

These surfaces are release-blocking. They carry SemVer expectations, migration notes, deprecation windows, and explicit compatibility jobs.

## Surface classes

### Public and stable

Stable surfaces require:

- SemVer discipline
- explicit versioning for breaking changes
- migration guidance for every breaking release
- a two-minor-release deprecation window
- release/nightly old-client-versus-new-server coverage

Current stable surfaces:

- HTTP API
- OpenAPI contract
- Python SDK
- TypeScript SDK
- Go SDK

### Public but evolving

These surfaces are supported and regression-tested, but are not yet treated as strict long-term compatibility contracts.

They require:

- explicit versioning
- changelog notes when behavior changes
- coverage for primary workflows
- promotion criteria before they become stable

Current evolving surfaces:

- MCP adapter
- Obsidian plugin
- docs quickstarts and operational guides

### Internal or non-contract

These surfaces are release-quality software, but not versioned compatibility promises.

Current internal/non-contract surfaces:

- dashboard
- internal CLI and deployment tooling

## Support window

The compatibility baseline starts at the current planning baseline and the earliest tagged release currently present in this repository: `v1.0-rc`.

The active support window is:

- current server against current SDKs in PR-fast jobs
- current server against previous tagged stable-source SDKs in nightly/release jobs

At the moment that means:

- previous Python SDK from `v1.0-rc`
- previous TypeScript SDK from `v1.0-rc`
- Go starts at the current baseline because no Go SDK exists in the `v1.0-rc` source tree

As additional releases are cut, this window should expand to “current plus previous minor” for each stable SDK.

## Migration policy

- The current code is the starting baseline for compatibility planning.
- Strict backward compatibility was not retroactively imposed on pre-baseline development.
- Every release after the baseline must provide a clear migration path forward.
- Breaking changes are allowed only with explicit versioning, migration guidance, and the deprecation window above.

## CI obligations

Fast PR gates cover:

- static analysis and package tests
- OpenAPI drift
- current-SDK live-node smoke

Nightly and release-oriented jobs cover:

- previous-release SDKs against the current server
- schema-upgrade checks from the `v1.0-rc` schema baseline
- quickstart Docker smoke
- docs build
- federation soak

This separation keeps PR latency reasonable without dropping release traceability.
