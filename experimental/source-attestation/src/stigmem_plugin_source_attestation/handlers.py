"""Hook handlers for the source-attestation plugin."""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError
from stigmem_node.plugins import Allow, Deny, PluginContext, PluginHealth, PluginHealthStatus

from .config import load_config_from_env


def config_validate(_ctx: PluginContext, **_: Any) -> Allow | Deny:
    """Validate operator gates before the plugin is registered."""

    try:
        load_config_from_env()
    except ValidationError as exc:
        return Deny(f"invalid source-attestation plugin config: {exc}")
    return Allow()


def pre_assert_validate(_ctx: PluginContext, **kwargs: Any) -> Allow | Deny:
    """Gate source/identity binding behind explicit plugin configuration."""

    config = load_config_from_env()
    if not (config.enabled and config.enforce_assert_validation):
        return Allow()

    req = kwargs.get("req")
    identity = kwargs.get("identity")
    source = getattr(req, "source", None)
    entity_uri = getattr(identity, "entity_uri", None)
    if source == entity_uri:
        return Allow()

    return Deny(
        "source_attestation_failed: declared source does not match authenticated principal"
    )


def recall_rank(_ctx: PluginContext, scored_results: list[Any], **kwargs: Any) -> dict[str, float]:
    """Contribute source-trust score deltas only when explicitly enabled."""

    config = load_config_from_env()
    if not (config.enabled and config.apply_recall_rank):
        return {}

    from stigmem_node.source_trust import compute_source_trust

    identity = kwargs.get("identity")
    weights = kwargs.get("weights")
    source_weight = float(getattr(weights, "source_trust", 0.0))
    if source_weight <= 0.0:
        return {}

    base_weight = (
        float(getattr(weights, "lexical", 0.0))
        + float(getattr(weights, "semantic", 0.0))
        + float(getattr(weights, "graph", 0.0))
        + source_weight
        + float(getattr(weights, "recency", 0.0))
    )
    if base_weight <= 0.0:
        base_weight = 1.0

    deltas: dict[str, float] = {}
    for scored in scored_results:
        fact = getattr(scored, "fact", None)
        fact_id = getattr(fact, "id", None)
        source = getattr(fact, "source", None)
        scope = getattr(fact, "scope", None)
        confidence = float(getattr(fact, "confidence", 0.0))
        if fact_id is None or source is None or scope is None:
            continue
        trust = compute_source_trust(source, scope, identity)
        deltas[str(fact_id)] = (source_weight * trust / base_weight) * max(0.0, confidence)

    return deltas


def federation_inbound_validate(_ctx: PluginContext, **kwargs: Any) -> Allow | Deny:
    """Gate inbound source-attestation policy behind explicit plugin configuration."""

    config = load_config_from_env()
    if not (config.enabled and config.enforce_federation_inbound):
        return Allow()

    fact = kwargs.get("fact") or {}
    fact_source = fact.get("source") if isinstance(fact, dict) else None
    peer = kwargs.get("peer") or {}
    cap_token = kwargs.get("cap_token") or {}
    expected_source = None
    if isinstance(peer, dict):
        expected_source = peer.get("node_id")
    if expected_source is None and isinstance(cap_token, dict):
        expected_source = cap_token.get("subject")
    if fact_source == expected_source:
        return Allow()

    return Deny("source_attestation_failed: federated fact source does not match sender")


def health_check(_ctx: PluginContext) -> PluginHealth:
    """Report scaffold health for registry lifecycle tests."""

    return PluginHealth(
        status=PluginHealthStatus.HEALTHY,
        message="source attestation plugin scaffold registered",
    )
