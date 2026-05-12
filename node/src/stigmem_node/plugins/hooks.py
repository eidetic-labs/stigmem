"""Stable PR 4-INF.1 hook definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .bands import Band


class HookSemantic(StrEnum):
    VOTING = "voting"
    FILTER_CHAIN = "filter_chain"
    SCORE_DELTA = "score_delta"
    FIRE_AND_FORGET = "fire_and_forget"


class HookOrdering(StrEnum):
    CORE_FIRST = "core_first"
    PLUGINS_FIRST = "plugins_first"
    CORE_ONLY_DEFAULT = "core_only_default"
    PLUGIN_ONLY = "plugin_only"


class HookName(StrEnum):
    PRE_ASSERT_AUTHORIZE = "pre_assert_authorize"
    PRE_ASSERT_VALIDATE = "pre_assert_validate"
    PRE_ASSERT_TRANSFORM = "pre_assert_transform"
    POST_ASSERT_PERSIST = "post_assert_persist"
    POST_ASSERT_PROPAGATE = "post_assert_propagate"
    POST_ASSERT_AUDIT = "post_assert_audit"
    PRE_RECALL_AUTHORIZE = "pre_recall_authorize"
    PRE_RECALL_REWRITE = "pre_recall_rewrite"
    RECALL_FILTER = "recall_filter"
    RECALL_RANK = "recall_rank"
    POST_RECALL_AUDIT = "post_recall_audit"
    FEDERATION_PEER_AUTHENTICATE = "federation_peer_authenticate"
    FEDERATION_INBOUND_VALIDATE = "federation_inbound_validate"
    FEDERATION_INBOUND_FILTER = "federation_inbound_filter"
    FEDERATION_OUTBOUND_FILTER = "federation_outbound_filter"
    FEDERATION_OUTBOUND_SIGN = "federation_outbound_sign"
    IDENTITY_RESOLVE = "identity_resolve"
    TENANT_RESOLVE = "tenant_resolve"
    CAPABILITY_CHECK = "capability_check"
    MIGRATION_REGISTER = "migration_register"
    AUDIT_EMIT = "audit_emit"
    CONFIG_VALIDATE = "config_validate"


@dataclass(frozen=True, slots=True)
class HookSpec:
    name: HookName
    band: Band
    semantic: HookSemantic
    ordering: HookOrdering
    strict_audit: bool = False


HOOK_SPECS: dict[str, HookSpec] = {
    HookName.PRE_ASSERT_AUTHORIZE.value: HookSpec(
        HookName.PRE_ASSERT_AUTHORIZE,
        Band.AUTHZ,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.PRE_ASSERT_VALIDATE.value: HookSpec(
        HookName.PRE_ASSERT_VALIDATE,
        Band.VALIDATE,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.PRE_ASSERT_TRANSFORM.value: HookSpec(
        HookName.PRE_ASSERT_TRANSFORM,
        Band.TRANSFORM,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.POST_ASSERT_PERSIST.value: HookSpec(
        HookName.POST_ASSERT_PERSIST,
        Band.PERSIST,
        HookSemantic.FIRE_AND_FORGET,
        HookOrdering.PLUGIN_ONLY,
    ),
    HookName.POST_ASSERT_PROPAGATE.value: HookSpec(
        HookName.POST_ASSERT_PROPAGATE,
        Band.PERSIST,
        HookSemantic.FIRE_AND_FORGET,
        HookOrdering.PLUGIN_ONLY,
    ),
    HookName.POST_ASSERT_AUDIT.value: HookSpec(
        HookName.POST_ASSERT_AUDIT,
        Band.AUDIT,
        HookSemantic.FIRE_AND_FORGET,
        HookOrdering.CORE_ONLY_DEFAULT,
        strict_audit=True,
    ),
    HookName.PRE_RECALL_AUTHORIZE.value: HookSpec(
        HookName.PRE_RECALL_AUTHORIZE,
        Band.AUTHZ,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.PRE_RECALL_REWRITE.value: HookSpec(
        HookName.PRE_RECALL_REWRITE,
        Band.TRANSFORM,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.RECALL_FILTER.value: HookSpec(
        HookName.RECALL_FILTER,
        Band.FILTER,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.RECALL_RANK.value: HookSpec(
        HookName.RECALL_RANK,
        Band.RANK,
        HookSemantic.SCORE_DELTA,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.POST_RECALL_AUDIT.value: HookSpec(
        HookName.POST_RECALL_AUDIT,
        Band.AUDIT,
        HookSemantic.FIRE_AND_FORGET,
        HookOrdering.CORE_ONLY_DEFAULT,
        strict_audit=True,
    ),
    HookName.FEDERATION_PEER_AUTHENTICATE.value: HookSpec(
        HookName.FEDERATION_PEER_AUTHENTICATE,
        Band.AUTHN,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.FEDERATION_INBOUND_VALIDATE.value: HookSpec(
        HookName.FEDERATION_INBOUND_VALIDATE,
        Band.VALIDATE,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.FEDERATION_INBOUND_FILTER.value: HookSpec(
        HookName.FEDERATION_INBOUND_FILTER,
        Band.FILTER,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.FEDERATION_OUTBOUND_FILTER.value: HookSpec(
        HookName.FEDERATION_OUTBOUND_FILTER,
        Band.FILTER,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.FEDERATION_OUTBOUND_SIGN.value: HookSpec(
        HookName.FEDERATION_OUTBOUND_SIGN,
        Band.TRANSFORM,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.PLUGINS_FIRST,
    ),
    HookName.IDENTITY_RESOLVE.value: HookSpec(
        HookName.IDENTITY_RESOLVE,
        Band.AUTHN,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.CORE_FIRST,
    ),
    HookName.TENANT_RESOLVE.value: HookSpec(
        HookName.TENANT_RESOLVE,
        Band.AUTHN,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.CORE_FIRST,
    ),
    HookName.CAPABILITY_CHECK.value: HookSpec(
        HookName.CAPABILITY_CHECK,
        Band.AUTHZ,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
    HookName.MIGRATION_REGISTER.value: HookSpec(
        HookName.MIGRATION_REGISTER,
        Band.TRANSFORM,
        HookSemantic.FILTER_CHAIN,
        HookOrdering.CORE_ONLY_DEFAULT,
    ),
    HookName.AUDIT_EMIT.value: HookSpec(
        HookName.AUDIT_EMIT,
        Band.AUDIT,
        HookSemantic.FIRE_AND_FORGET,
        HookOrdering.CORE_ONLY_DEFAULT,
        strict_audit=True,
    ),
    HookName.CONFIG_VALIDATE.value: HookSpec(
        HookName.CONFIG_VALIDATE,
        Band.VALIDATE,
        HookSemantic.VOTING,
        HookOrdering.CORE_FIRST,
    ),
}

KNOWN_HOOKS = frozenset(HOOK_SPECS)
