"""Plugin signing verification boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .discovery import DiscoveredPlugin
from .errors import PluginSignatureError


def _parse_identity_set(raw: str) -> frozenset[str]:
    return frozenset(identity.strip() for identity in raw.split(",") if identity.strip())


@dataclass(frozen=True, slots=True)
class PluginTrustPolicy:
    """Operator-configured plugin publisher trust policy."""

    trusted_publishers: frozenset[str] = frozenset()
    override_publishers: frozenset[str] = frozenset()

    @classmethod
    def from_settings(cls) -> PluginTrustPolicy:
        from stigmem_node.settings import settings

        return cls(
            trusted_publishers=_parse_identity_set(settings.plugin_trusted_publishers),
            override_publishers=_parse_identity_set(settings.plugin_trust_override_publishers),
        )


@dataclass(frozen=True, slots=True)
class PluginSigningInfo:
    """Verified plugin signing metadata used during registration."""

    signing_identity: str
    trust_decision: str
    trust_reason: str | None = None

    def audit_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {"trust_decision": self.trust_decision}
        if self.trust_reason is not None:
            metadata["trust_reason"] = self.trust_reason
        return metadata


PluginSignatureVerifier = Callable[[DiscoveredPlugin], PluginSigningInfo]


def require_verified_signature(
    plugin: DiscoveredPlugin,
    *,
    policy: PluginTrustPolicy | None = None,
) -> PluginSigningInfo:
    """Return signing metadata for a pre-verified plugin or fail closed.

    PR 4-INF.3 wires the production registration gate here. Package-manager and
    trusted-publisher policy work can replace this verifier with a Sigstore
    implementation without changing the registry contract.
    """

    if not plugin.signature_verified or plugin.signing_identity == "unsigned":
        raise PluginSignatureError(
            f"plugin {plugin.manifest.name!r} is unsigned; "
            "production plugin registration requires Sigstore verification"
        )
    trust_policy = policy or PluginTrustPolicy.from_settings()
    if plugin.signing_identity in trust_policy.trusted_publishers:
        return PluginSigningInfo(
            signing_identity=plugin.signing_identity,
            trust_decision="trusted_publisher",
        )
    if plugin.signing_identity in trust_policy.override_publishers:
        return PluginSigningInfo(
            signing_identity=plugin.signing_identity,
            trust_decision="operator_override",
            trust_reason="signing identity accepted by explicit operator override",
        )
    raise PluginSignatureError(
        f"plugin {plugin.manifest.name!r} is signed by untrusted identity "
        f"{plugin.signing_identity!r}; add it to STIGMEM_PLUGIN_TRUSTED_PUBLISHERS "
        "or, for an explicit audited exception, "
        "STIGMEM_PLUGIN_TRUST_OVERRIDE_PUBLISHERS"
    )
