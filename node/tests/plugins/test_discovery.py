from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

import stigmem_node.plugins.discovery as discovery
from stigmem_node.plugins import (
    ENTRY_POINT_GROUP,
    DiscoveredPlugin,
    PluginDependencyError,
    PluginDiscoveryError,
    PluginManifest,
    discover_plugin_manifests,
    resolve_plugin_dependencies,
)


def _manifest(name: str, *, depends_on: frozenset[str] = frozenset()) -> PluginManifest:
    return PluginManifest(name=name, version="1.0.0", depends_on=depends_on)


@dataclass(frozen=True)
class _Dist:
    metadata: dict[str, str]


@dataclass(frozen=True)
class _EntryPoint:
    name: str
    value: str
    loaded: Any
    group: str = ENTRY_POINT_GROUP
    dist: _Dist | None = None

    def load(self) -> Any:
        if isinstance(self.loaded, BaseException):
            raise self.loaded
        return self.loaded


class _EntryPointSet(list[_EntryPoint]):
    def select(self, *, group: str) -> _EntryPointSet:
        return _EntryPointSet([entry_point for entry_point in self if entry_point.group == group])


def _set_entry_points(monkeypatch: pytest.MonkeyPatch, *entry_points: _EntryPoint) -> None:
    monkeypatch.setattr(discovery, "entry_points", lambda: _EntryPointSet(entry_points))


def test_discover_plugin_manifests_loads_entry_point_factories(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(
            name="bbb-entry",
            value="pkg_b:create",
            loaded=lambda: _manifest("bbb-plugin"),
            dist=_Dist({"Name": "pkg-b"}),
        ),
        _EntryPoint(
            name="aaa-entry",
            value="pkg_a:create",
            loaded=lambda: _manifest("aaa-plugin"),
            dist=_Dist({"Name": "pkg-a"}),
        ),
    )

    discovered = discover_plugin_manifests()

    assert [item.manifest.name for item in discovered] == ["aaa-plugin", "bbb-plugin"]
    assert discovered[0].entry_point_name == "aaa-entry"
    assert discovered[0].entry_point_value == "pkg_a:create"
    assert discovered[0].distribution == "pkg-a"


def test_discover_plugin_manifests_ignores_other_entry_point_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(
            name="other-entry",
            value="pkg:create",
            loaded=lambda: _manifest("other-plugin"),
            group="other.plugins",
        ),
    )

    assert discover_plugin_manifests() == ()


def test_discover_plugin_manifests_rejects_load_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(name="bad-entry", value="pkg:create", loaded=ImportError("boom")),
    )

    with pytest.raises(PluginDiscoveryError, match="failed to load.*bad-entry.*boom"):
        discover_plugin_manifests()


def test_discover_plugin_manifests_rejects_non_callable_entry_point(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(name="bad-entry", value="pkg:manifest", loaded=_manifest("aaa-plugin")),
    )

    with pytest.raises(PluginDiscoveryError, match="bad-entry.*expected a callable"):
        discover_plugin_manifests()


def test_discover_plugin_manifests_rejects_factory_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def explode() -> PluginManifest:
        raise ValueError("invalid config")

    _set_entry_points(
        monkeypatch,
        _EntryPoint(name="bad-entry", value="pkg:create", loaded=explode),
    )

    with pytest.raises(PluginDiscoveryError, match="bad-entry.*invalid config"):
        discover_plugin_manifests()


def test_discover_plugin_manifests_rejects_non_manifest_return(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(name="bad-entry", value="pkg:create", loaded=object),
    )

    with pytest.raises(PluginDiscoveryError, match="bad-entry.*expected PluginManifest"):
        discover_plugin_manifests()


def test_discover_plugin_manifests_rejects_duplicate_plugin_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_entry_points(
        monkeypatch,
        _EntryPoint(name="aaa-entry", value="pkg_a:create", loaded=lambda: _manifest("same")),
        _EntryPoint(name="bbb-entry", value="pkg_b:create", loaded=lambda: _manifest("same")),
    )

    with pytest.raises(
        PluginDiscoveryError,
        match="duplicate plugin name 'same'.*aaa-entry.*bbb-entry",
    ):
        discover_plugin_manifests()


def test_resolve_plugin_dependencies_orders_dependencies_first() -> None:
    base = DiscoveredPlugin(_manifest("base"), "base-entry", "pkg_base:create")
    addon = DiscoveredPlugin(
        _manifest("addon", depends_on=frozenset({"base"})),
        "addon-entry",
        "pkg_addon:create",
    )

    ordered = resolve_plugin_dependencies([addon, base])

    assert [plugin.manifest.name for plugin in ordered] == ["base", "addon"]


def test_resolve_plugin_dependencies_orders_multiple_roots_deterministically() -> None:
    alpha = DiscoveredPlugin(_manifest("alpha"), "z-entry", "pkg_alpha:create")
    beta = DiscoveredPlugin(_manifest("beta"), "a-entry", "pkg_beta:create")
    leaf = DiscoveredPlugin(
        _manifest("leaf", depends_on=frozenset({"alpha", "beta"})),
        "leaf-entry",
        "pkg_leaf:create",
    )

    ordered = resolve_plugin_dependencies([leaf, beta, alpha])

    assert [plugin.manifest.name for plugin in ordered] == ["alpha", "beta", "leaf"]


def test_resolve_plugin_dependencies_allows_registered_dependencies() -> None:
    addon = DiscoveredPlugin(
        _manifest("addon", depends_on=frozenset({"core-plugin"})),
        "addon-entry",
        "pkg_addon:create",
    )

    ordered = resolve_plugin_dependencies([addon], registered_plugins={"core-plugin"})

    assert [plugin.manifest.name for plugin in ordered] == ["addon"]


def test_resolve_plugin_dependencies_rejects_missing_dependency() -> None:
    addon = DiscoveredPlugin(
        _manifest("addon", depends_on=frozenset({"missing-a", "missing-b"})),
        "addon-entry",
        "pkg_addon:create",
    )

    with pytest.raises(
        PluginDependencyError,
        match="addon missing missing-a, missing-b",
    ):
        resolve_plugin_dependencies([addon])


def test_resolve_plugin_dependencies_rejects_cycle_with_path() -> None:
    alpha = DiscoveredPlugin(
        _manifest("alpha", depends_on=frozenset({"gamma"})),
        "alpha-entry",
        "pkg_alpha:create",
    )
    beta = DiscoveredPlugin(
        _manifest("beta", depends_on=frozenset({"alpha"})),
        "beta-entry",
        "pkg_beta:create",
    )
    gamma = DiscoveredPlugin(
        _manifest("gamma", depends_on=frozenset({"beta"})),
        "gamma-entry",
        "pkg_gamma:create",
    )

    with pytest.raises(
        PluginDependencyError,
        match="alpha -> gamma -> beta -> alpha",
    ):
        resolve_plugin_dependencies([alpha, beta, gamma])
