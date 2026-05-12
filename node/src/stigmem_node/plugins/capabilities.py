"""Capability names exposed to plugins."""

from __future__ import annotations

from enum import StrEnum


class Capability(StrEnum):
    FACTS_READ = "facts.read"
    FACTS_WRITE = "facts.write"
    RECALL_READ = "recall.read"
    RECALL_WRITE = "recall.write"
    AUDIT_EMIT = "audit.emit"
    AUDIT_READ = "audit.read"
    FEDERATION_READ = "federation.read"
    FEDERATION_WRITE = "federation.write"
    IDENTITY_READ = "identity.read"
    TENANT_READ = "tenant.read"
    TENANT_WRITE = "tenant.write"
    CONFIG_READ = "config.read"
    NETWORK_OUTBOUND = "network.outbound"


CAPABILITY_ALLOWLIST = frozenset(cap.value for cap in Capability)
