---
title: Plugin Capability Reference
sidebar_label: Capabilities
description: Stable v0.9.0a1 plugin capability names, context accessors, and fail-closed behavior.
audience: Security
---

# Plugin Capability Reference

<p className="stigmem-meta"><span>3 min read</span><span>Plugin author · Security reviewer</span><span>v0.9.0a1 stable</span></p>

<div className="stigmem-lead">

**What this page covers**

Stigmem plugins declare capabilities in `PluginManifest.capabilities`.
The registry passes each handler a `PluginContext` scoped to the
declaring plugin. A handler can only retrieve a core API handle
when the manifest declares the matching capability.

</div>

**Audience:** Plugin authors, operators, and security reviewers evaluating plugin access.

<div className="stigmem-keypoint">

**The v0.9.0a1 capability model is intentionally fail closed.**

<div className="stigmem-grid">

<div><h4>Unknown names rejected</h4><p>During manifest validation.</p></div>
<div><h4>Missing declared capabilities raise</h4><p><code>CapabilityError</code> when a handler calls the gated accessor.</p></div>
<div><h4>Declaring ≠ guarantee</h4><p>Declaring a capability permits access, but the exposed handle may still be <code>None</code> if the node did not provide that core API to plugins.</p></div>
<div><h4>Not a replacement</h4><p>Treat capabilities as security review inputs, not as a replacement for plugin signing, trusted-publisher policy, or code review.</p></div>

</div>

</div>

For a working example, see the [Plugin Author Guide](../../guides/plugins/author-guide.md). For hook dispatch behavior, see the [Plugin Hook Reference](./hooks.md).

## Capability table

<div className="stigmem-fields">

<div>
<dt>Capability</dt>
<dt><span className="stigmem-fields__type">Accessor</span></dt>
<dd>Access · review guidance</dd>
</div>

<div>
<dt><code>facts.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_facts_reader()</code></span></dt>
<dd>Read-oriented fact access. Verify the plugin has a need to inspect facts in the scopes it will operate on.</dd>
</div>

<div>
<dt><code>facts.write</code></dt>
<dt><span className="stigmem-fields__type"><code>get_facts_writer()</code></span></dt>
<dd>Write-oriented fact access. <strong>High impact.</strong> Confirm writes are namespaced, auditable, and bounded by operator policy.</dd>
</div>

<div>
<dt><code>recall.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_recall_reader()</code></span></dt>
<dd>Read-oriented recall access. Review data exposure risk because recall may combine multiple facts into richer context.</dd>
</div>

<div>
<dt><code>recall.write</code></dt>
<dt><span className="stigmem-fields__type"><code>get_recall_writer()</code></span></dt>
<dd>Write or mutation access for recall state. <strong>High impact.</strong> Confirm the plugin cannot poison ranking or recall state outside its intended scope.</dd>
</div>

<div>
<dt><code>audit.emit</code></dt>
<dt><span className="stigmem-fields__type"><code>get_audit_emitter()</code></span></dt>
<dd>Emit audit events. Does not grant read access to audit history.</dd>
</div>

<div>
<dt><code>audit.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_audit_reader()</code></span></dt>
<dd>Read audit data. <strong>Sensitive.</strong> Audit trails can reveal actors, target entities, tenant identifiers, and operational metadata.</dd>
</div>

<div>
<dt><code>federation.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_federation_reader()</code></span></dt>
<dd>Read federation state. Review peer metadata exposure and whether the plugin can infer trust relationships.</dd>
</div>

<div>
<dt><code>federation.write</code></dt>
<dt><span className="stigmem-fields__type"><code>get_federation_writer()</code></span></dt>
<dd>Write or mutation access. <strong>High impact.</strong> Federation mutation can affect peer behavior and propagation.</dd>
</div>

<div>
<dt><code>identity.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_identity_reader()</code></span></dt>
<dd>Read identity state. <strong>Sensitive.</strong> Identity metadata can affect authorization, attribution, and audit review.</dd>
</div>

<div>
<dt><code>tenant.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_tenant_reader()</code></span></dt>
<dd>Read tenant context. Review multi-tenant boundary impact.</dd>
</div>

<div>
<dt><code>tenant.write</code></dt>
<dt><span className="stigmem-fields__type"><code>get_tenant_writer()</code></span></dt>
<dd>Write or mutation access. <strong>High impact.</strong> Tenant mutation can affect isolation and routing.</dd>
</div>

<div>
<dt><code>config.read</code></dt>
<dt><span className="stigmem-fields__type"><code>get_config_reader()</code></span></dt>
<dd>Read node or plugin configuration. Review whether configuration contains secrets, trusted publisher identities, or topology.</dd>
</div>

<div>
<dt><code>network.outbound</code></dt>
<dt><span className="stigmem-fields__type"><code>get_network_outbound()</code></span></dt>
<dd>Outbound network access. <strong>High impact.</strong> Review destination allowlists, data exfiltration risk, and timeout behavior.</dd>
</div>

</div>

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

<div className="stigmem-grid">

<div><h4>Voting / filter / score-delta</h4><p>Failures surface as plugin execution errors.</p></div>
<div><h4>Non-strict fire-and-forget</h4><p>Logged and audited without stopping the hook site.</p></div>
<div><h4>Strict audit (incl. <code>audit_emit</code>)</h4><p>Failures are surfaced.</p></div>

</div>

## Operator review checklist

<ol className="stigmem-steps">
<li>Confirm the package is signed by an accepted trusted publisher or an explicit operator override.</li>
<li>Compare the manifest capability list to the plugin's documented behavior.</li>
<li>Reject broad write, tenant, federation, identity, or outbound-network access unless the use case requires it.</li>
<li>Prefer plugins that emit audit events for meaningful side effects.</li>
<li>Re-review capabilities when upgrading a plugin package, even if the signing identity has not changed.</li>
</ol>
