---
title: Plugin Capability Reference
sidebar_label: Capabilities
description: Stable v0.9.0a1 plugin capability names, context accessors, and fail-closed behavior.
audience: Security
---

# Plugin Capability Reference

**Audience:** Plugin authors, operators, and security reviewers evaluating plugin access.

Stigmem plugins declare capabilities in `PluginManifest.capabilities`. The registry passes each handler a `PluginContext` scoped to the declaring plugin. A handler can only retrieve a core API handle when the manifest declares the matching capability.

The v0.9.0a1 capability model is intentionally fail closed:

- Unknown capability names are rejected during manifest validation.
- Missing declared capabilities raise `CapabilityError` when a handler calls the gated accessor.
- Declaring a capability permits access to that context accessor, but the exposed handle may still be `None` if the node did not provide that core API to plugins.
- Operators should treat capabilities as security review inputs, not as a replacement for plugin signing, trusted-publisher policy, or code review.

For a working example, see the [Plugin Author Guide](../../guides/plugins/author-guide.md). For hook dispatch behavior, see the [Plugin Hook Reference](./hooks.md).

## Capability table

| Capability | Context accessor | Access enabled | Review guidance |
|---|---|---|---|
| `facts.read` | `ctx.get_facts_reader()` | Read-oriented fact access exposed by the node. | Verify the plugin has a need to inspect facts in the scopes it will operate on. |
| `facts.write` | `ctx.get_facts_writer()` | Write-oriented fact access exposed by the node. | Treat as high impact. Confirm writes are namespaced, auditable, and bounded by operator policy. |
| `recall.read` | `ctx.get_recall_reader()` | Read-oriented recall access exposed by the node. | Review data exposure risk because recall may combine multiple facts into richer context. |
| `recall.write` | `ctx.get_recall_writer()` | Write or mutation access for recall-related state exposed by the node. | Treat as high impact. Confirm the plugin cannot poison ranking or recall state outside its intended scope. |
| `audit.emit` | `ctx.get_audit_emitter()` | Emit audit events through the node-provided audit emitter. | Prefer this for plugins with meaningful side effects. Audit emission does not grant read access to audit history. |
| `audit.read` | `ctx.get_audit_reader()` | Read audit data exposed by the node. | Treat as sensitive. Audit trails can reveal actors, target entities, tenant identifiers, and operational metadata. |
| `federation.read` | `ctx.get_federation_reader()` | Read federation state exposed by the node. | Review peer metadata exposure and whether the plugin can infer trust relationships. |
| `federation.write` | `ctx.get_federation_writer()` | Write or mutation access for federation state exposed by the node. | Treat as high impact. Federation mutation can affect peer behavior and propagation. |
| `identity.read` | `ctx.get_identity_reader()` | Read identity state exposed by the node. | Treat as sensitive. Identity metadata can affect authorization, attribution, and audit review. |
| `tenant.read` | `ctx.get_tenant_reader()` | Read tenant context exposed by the node. | Review multi-tenant boundary impact and avoid exposing unrelated tenant metadata. |
| `tenant.write` | `ctx.get_tenant_writer()` | Write or mutation access for tenant state exposed by the node. | Treat as high impact. Tenant mutation can affect isolation and routing. |
| `config.read` | `ctx.get_config_reader()` | Read node or plugin configuration exposed by the node. | Review whether configuration contains secrets, trusted publisher identities, or deployment topology. |
| `network.outbound` | `ctx.get_network_outbound()` | Outbound network access exposed by the node. | Treat as high impact. Review destination allowlists, data exfiltration risk, and timeout behavior. |

## Denial behavior

Capability denial is enforced when the handler asks for a core API handle:

```python
from stigmem_node.plugins import PluginContext


def handler(ctx: PluginContext, **_: object) -> None:
    ctx.get_facts_reader()
```

If the plugin manifest does not declare `facts.read`, the accessor raises `CapabilityError`:

```text
plugin 'example-plugin' cannot call get_facts_reader: capability 'facts.read' not declared
```

The registry treats that like any other handler failure for the hook semantic:

- Voting, filter-chain, and score-delta hook failures surface as plugin execution errors.
- Non-strict fire-and-forget hook failures are logged and audited without stopping the hook site.
- Strict audit hooks, including `audit_emit`, surface the failure.

## Operator review checklist

Before enabling a plugin:

- Confirm the package is signed by an accepted trusted publisher or an explicit operator override.
- Compare the manifest capability list to the plugin's documented behavior.
- Reject broad write, tenant, federation, identity, or outbound-network access unless the use case requires it.
- Prefer plugins that emit audit events for meaningful side effects.
- Re-review capabilities when upgrading a plugin package, even if the signing identity has not changed.
