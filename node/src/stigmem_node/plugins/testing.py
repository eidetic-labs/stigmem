"""Testing helpers for controlled plugin registry state."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from .manifest import PluginManifest
from .registry import HookRegistry, set_registry


class TestPluginRegistry(HookRegistry):
    """Named test subclass for fixtures and downstream plugin tests."""


@contextmanager
def stigmem_plugins(manifests: list[PluginManifest]) -> Iterator[TestPluginRegistry]:
    """Temporarily replace the process registry with test plugin manifests."""
    registry = TestPluginRegistry()
    for manifest in manifests:
        registry.register_plugin(manifest)
    previous = set_registry(registry)
    try:
        yield registry
    finally:
        set_registry(previous)
