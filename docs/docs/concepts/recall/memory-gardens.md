---
title: Memory Gardens
sidebar_label: Memory Gardens
audience: Integrator
status: Experimental
---

# Memory Gardens

**Audience:** Agent developers and node operators creating named, access-controlled partitions within a scope.

:::info Coming soon
This guide covers Memory Gardens , a v0.9 addition. Spec draft is in progress.
:::

A Memory Garden is a named, ACL'd partition that sits inside a scope. Members have `admin`, `writer`, or `reader` roles. Garden ACL is enforced at both read and write time, layered on top of existing scope enforcement.

Key properties:
- Garden-tagged facts carry a `garden_id` URI field (§2.7)
- Garden facts **never** federate — they stay local to the originating node
- Gardens are created and managed via the garden CRUD API (§17)

When shipped, this guide will cover garden creation, membership management, and access control.
