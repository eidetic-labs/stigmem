---
title: Plugin Hook Reference
sidebar_label: Hooks
description: Stable v0.9.0a1 plugin hook names, semantics, ordering policies, and handler shapes.
audience: Integrator
---

# Plugin Hook Reference

<p className="stigmem-meta"><span>3 min read</span><span>Plugin author · Integrator</span><span>v0.9.0a1 stable</span></p>

<div className="stigmem-lead">

**What this page covers**

The 22-hook surface defined for PR 4-INF.1 and used by the v0.9.0aN
plugin infrastructure. Aligned with
`node/src/stigmem_node/plugins/hooks.py`.

</div>

<div className="stigmem-keypoint">

**Do not add hook names beyond this list for v0.9.0a1-compatible plugins.**

</div>

For a complete package example, start with the [Plugin Author Guide](../../guides/plugins/author-guide.md).

## Handler semantics

Every handler receives a `PluginContext` as its first positional argument. Hook-site payloads are passed as keyword arguments unless the semantic says a current value is passed positionally.

<div className="stigmem-fields">

<div>
<dt>Semantic</dt>
<dt><span className="stigmem-fields__type">Registry</span></dt>
<dd>Handler shape · return</dd>
</div>

<div>
<dt><code>voting</code></dt>
<dt><span className="stigmem-fields__type"><code>fire_voting</code></span></dt>
<dd><code>def handler(ctx, **kwargs) -&gt; Allow | Deny</code>. Return <code>Allow()</code> or <code>Deny("reason")</code>.</dd>
</div>

<div>
<dt><code>filter_chain</code></dt>
<dt><span className="stigmem-fields__type"><code>fire_filter_chain</code></span></dt>
<dd><code>def handler(ctx, value, **kwargs) -&gt; T</code>. The transformed value. Returning <code>None</code> is an error.</dd>
</div>

<div>
<dt><code>score_delta</code></dt>
<dt><span className="stigmem-fields__type"><code>fire_score_delta</code></span></dt>
<dd><code>def handler(ctx, scored_results, **kwargs) -&gt; dict[str, float]</code>. Score deltas keyed by result or fact id. Summed across handlers.</dd>
</div>

<div>
<dt><code>fire_and_forget</code></dt>
<dt><span className="stigmem-fields__type"><code>fire_fire_and_forget</code></span></dt>
<dd><code>def handler(ctx, **kwargs) -&gt; None</code>. Audit hooks marked strict raise on handler failure.</dd>
</div>

</div>

## Ordering policies

<div className="stigmem-fields">

<div>
<dt>Policy</dt>
<dt><span className="stigmem-fields__type">Order</span></dt>
<dd>Meaning</dd>
</div>

<div>
<dt><code>core_first</code></dt>
<dt><span className="stigmem-fields__type">core → plugins</span></dt>
<dd>Core handlers run first, then plugin handlers in deterministic plugin order.</dd>
</div>

<div>
<dt><code>plugins_first</code></dt>
<dt><span className="stigmem-fields__type">plugins → core</span></dt>
<dd>Plugin handlers run before any core handlers.</dd>
</div>

<div>
<dt><code>core_only_default</code></dt>
<dt><span className="stigmem-fields__type">core baseline</span></dt>
<dd>Core behavior is the default path; plugins may observe or extend where registered.</dd>
</div>

<div>
<dt><code>plugin_only</code></dt>
<dt><span className="stigmem-fields__type">plugins only</span></dt>
<dd>Only plugin handlers run for the hook.</dd>
</div>

</div>

## Stable hook surface

<div className="stigmem-fields">

<div>
<dt>Hook</dt>
<dt><span className="stigmem-fields__type">Semantic · Ordering</span></dt>
<dd>Notes</dd>
</div>

<div>
<dt><code>pre_assert_authorize</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Authorize a fact assertion before validation and persistence.</dd>
</div>

<div>
<dt><code>pre_assert_validate</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Validate an assertion payload before transformation.</dd>
</div>

<div>
<dt><code>pre_assert_transform</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Rewrite or normalize the assertion payload.</dd>
</div>

<div>
<dt><code>post_assert_persist</code></dt>
<dt><span className="stigmem-fields__type">fire_and_forget · plugin_only</span></dt>
<dd>Observe post-persistence assertion effects.</dd>
</div>

<div>
<dt><code>post_assert_propagate</code></dt>
<dt><span className="stigmem-fields__type">fire_and_forget · plugin_only</span></dt>
<dd>Observe propagation scheduling after assertion.</dd>
</div>

<div>
<dt><code>post_assert_audit</code></dt>
<dt><span className="stigmem-fields__type">fire_and_forget · core_only_default</span></dt>
<dd>Strict audit hook. Handler failure is surfaced.</dd>
</div>

<div>
<dt><code>pre_recall_authorize</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Authorize a recall request.</dd>
</div>

<div>
<dt><code>pre_recall_rewrite</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Rewrite the recall query or request payload.</dd>
</div>

<div>
<dt><code>recall_filter</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Filter recall candidates or result collections.</dd>
</div>

<div>
<dt><code>recall_rank</code></dt>
<dt><span className="stigmem-fields__type">score_delta · plugins_first</span></dt>
<dd>Add rank score deltas by result or fact id.</dd>
</div>

<div>
<dt><code>post_recall_audit</code></dt>
<dt><span className="stigmem-fields__type">fire_and_forget · core_only_default</span></dt>
<dd>Strict audit hook for recall completion.</dd>
</div>

<div>
<dt><code>federation_peer_authenticate</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Authenticate a federation peer.</dd>
</div>

<div>
<dt><code>federation_inbound_validate</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Validate inbound federation data.</dd>
</div>

<div>
<dt><code>federation_inbound_filter</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Filter or rewrite inbound federation facts.</dd>
</div>

<div>
<dt><code>federation_outbound_filter</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Filter outbound federation payloads.</dd>
</div>

<div>
<dt><code>federation_outbound_sign</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · plugins_first</span></dt>
<dd>Add or transform outbound signing material.</dd>
</div>

<div>
<dt><code>identity_resolve</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · core_first</span></dt>
<dd>Resolve identity context from authentication material.</dd>
</div>

<div>
<dt><code>tenant_resolve</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · core_first</span></dt>
<dd>Resolve tenant context for a request.</dd>
</div>

<div>
<dt><code>capability_check</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Authorize capability use.</dd>
</div>

<div>
<dt><code>migration_register</code></dt>
<dt><span className="stigmem-fields__type">filter_chain · core_only_default</span></dt>
<dd>Register plugin-owned migrations; must remain namespaced to their declaring plugin.</dd>
</div>

<div>
<dt><code>audit_emit</code></dt>
<dt><span className="stigmem-fields__type">fire_and_forget · core_only_default</span></dt>
<dd>Strict audit hook for normalized audit events. Handler failure is surfaced.</dd>
</div>

<div>
<dt><code>config_validate</code></dt>
<dt><span className="stigmem-fields__type">voting · core_first</span></dt>
<dd>Validate plugin or node configuration before registration proceeds.</dd>
</div>

</div>

## Lifecycle health is not a hook

<div className="stigmem-keypoint">

**`health_check` is a `PluginManifest` lifecycle callable, not a hook.**

It is used by operator inspection and health reporting. It is not
part of the 22-hook PR 4-INF.1 surface and must not appear in the
manifest `hooks` mapping.

</div>
