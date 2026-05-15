"""Plugin signing verification boundary."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .discovery import DiscoveredPlugin
from .errors import PluginSignatureError


@dataclass(frozen=True, slots=True)
class PluginSigningInfo:
    """Verified plugin signing metadata used during registration."""

    signing_identity: str


PluginSignatureVerifier = Callable[[DiscoveredPlugin], PluginSigningInfo]


def require_verified_signature(plugin: DiscoveredPlugin) -> PluginSigningInfo:
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
    return PluginSigningInfo(signing_identity=plugin.signing_identity)
