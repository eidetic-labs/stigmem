"""Plugin registry exception types."""

from __future__ import annotations


class PluginExecutionError(RuntimeError):
    """Raised when a plugin handler violates a hook contract."""


class CapabilityError(PermissionError):
    """Raised when a plugin attempts to access an undeclared capability."""


class ManifestError(ValueError):
    """Raised when a plugin manifest is invalid for this registry."""


class RegistryFrozenError(RuntimeError):
    """Raised when startup-only registry mutation is attempted after freeze."""


class RejectError(RuntimeError):
    """Handler-level shortcut for a voting denial."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
