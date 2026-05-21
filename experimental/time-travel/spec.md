---
spec_id: Spec-X3-Time-Travel-Queries
version: 0.1.0-alpha.0
status: Experimental
applies_to: future experimental plugin line
last_updated: 2026-05-21
supersedes: pre-reset section 24 time-travel/as-of query material
depends_on:
  - Spec-01-Fact-Model >= 0.1.0-alpha.0
  - Spec-X2-RTBF-Tombstones >= 0.1.0-alpha.0
title: Time-Travel / As-Of Queries
sidebar_label: Time-Travel / As-Of Queries
audience: Spec
description: "Compatibility pointer for time-travel query semantics."
stability: experimental
since: 0.9.0a1
---

# Spec-X3-Time-Travel-Queries

This file is a compatibility pointer for existing `experimental/time-travel/`
links.

The canonical ADR-020 feature record now lives at
[`features/time-travel/`](../../features/time-travel/). The canonical
normative spec is [`features/time-travel/spec.md`](../../features/time-travel/spec.md).

The implementation package remains in `experimental/time-travel/` during the
transition. The feature record owns product truth; this directory owns the
current source package until a future packaging move is explicitly planned.
