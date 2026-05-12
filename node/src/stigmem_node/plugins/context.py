"""Capability-gated plugin context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import CapabilityError


@dataclass(frozen=True, slots=True)
class CoreApis:
    """Handles core chooses to expose to plugins.

    PR 4-INF.1 keeps this deliberately small and optional; later PRs can replace
    these generic handles with narrower typed facades without changing the
    registry contract.
    """

    facts_reader: Any = None
    facts_writer: Any = None
    recall_reader: Any = None
    recall_writer: Any = None
    audit_emitter: Any = None
    audit_reader: Any = None
    federation_reader: Any = None
    federation_writer: Any = None
    identity_reader: Any = None
    tenant_reader: Any = None
    tenant_writer: Any = None
    config_reader: Any = None
    network_outbound: Any = None


class PluginContext:
    """Capability-restricted context passed to plugin handlers."""

    __slots__ = ("_capabilities", "_core_apis", "plugin_name")

    def __init__(
        self,
        *,
        plugin_name: str,
        capabilities: frozenset[str],
        core_apis: CoreApis | None = None,
    ) -> None:
        self.plugin_name = plugin_name
        self._capabilities = capabilities
        self._core_apis = core_apis or CoreApis()

    @property
    def capabilities(self) -> frozenset[str]:
        return self._capabilities

    def _require(self, capability: str, accessor: str, value: Any) -> Any:
        if capability not in self._capabilities:
            raise CapabilityError(
                f"plugin {self.plugin_name!r} cannot call {accessor}: "
                f"capability {capability!r} not declared"
            )
        return value

    def get_facts_reader(self) -> Any:
        return self._require("facts.read", "get_facts_reader", self._core_apis.facts_reader)

    def get_facts_writer(self) -> Any:
        return self._require("facts.write", "get_facts_writer", self._core_apis.facts_writer)

    def get_recall_reader(self) -> Any:
        return self._require("recall.read", "get_recall_reader", self._core_apis.recall_reader)

    def get_recall_writer(self) -> Any:
        return self._require("recall.write", "get_recall_writer", self._core_apis.recall_writer)

    def get_audit_emitter(self) -> Any:
        return self._require("audit.emit", "get_audit_emitter", self._core_apis.audit_emitter)

    def get_audit_reader(self) -> Any:
        return self._require("audit.read", "get_audit_reader", self._core_apis.audit_reader)

    def get_federation_reader(self) -> Any:
        return self._require(
            "federation.read", "get_federation_reader", self._core_apis.federation_reader
        )

    def get_federation_writer(self) -> Any:
        return self._require(
            "federation.write", "get_federation_writer", self._core_apis.federation_writer
        )

    def get_identity_reader(self) -> Any:
        return self._require(
            "identity.read", "get_identity_reader", self._core_apis.identity_reader
        )

    def get_tenant_reader(self) -> Any:
        return self._require("tenant.read", "get_tenant_reader", self._core_apis.tenant_reader)

    def get_tenant_writer(self) -> Any:
        return self._require("tenant.write", "get_tenant_writer", self._core_apis.tenant_writer)

    def get_config_reader(self) -> Any:
        return self._require("config.read", "get_config_reader", self._core_apis.config_reader)

    def get_network_outbound(self) -> Any:
        return self._require(
            "network.outbound", "get_network_outbound", self._core_apis.network_outbound
        )
