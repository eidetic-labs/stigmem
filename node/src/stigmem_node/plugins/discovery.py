"""Plugin package discovery via Python entry points."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import EntryPoint, entry_points
from typing import Any

from .errors import PluginDiscoveryError
from .manifest import PluginManifest

ENTRY_POINT_GROUP = "stigmem.plugins"


@dataclass(frozen=True, slots=True)
class DiscoveredPlugin:
    """Plugin manifest loaded from a package entry point."""

    manifest: PluginManifest
    entry_point_name: str
    entry_point_value: str
    distribution: str | None = None


def discover_plugin_manifests(
    *, group: str = ENTRY_POINT_GROUP
) -> tuple[DiscoveredPlugin, ...]:
    """Load plugin manifests declared through Python package entry points.

    Entry points in ``stigmem.plugins`` must resolve to a zero-argument callable
    returning a :class:`PluginManifest`. PR 4-INF.2 keeps discovery separate from
    registration so dependency ordering and startup lifecycle can build on this
    deterministic manifest list.
    """

    discovered: list[DiscoveredPlugin] = []
    seen_names: dict[str, str] = {}
    for entry_point in sorted(_entry_points_for_group(group), key=lambda ep: ep.name):
        factory = _load_entry_point(entry_point)
        if not callable(factory):
            raise PluginDiscoveryError(
                f"plugin entry point {entry_point.name!r} loaded "
                f"{type(factory).__name__}; expected a callable returning PluginManifest"
            )
        manifest = _call_manifest_factory(entry_point, factory)
        previous_entry_point = seen_names.get(manifest.name)
        if previous_entry_point is not None:
            raise PluginDiscoveryError(
                f"duplicate plugin name {manifest.name!r} discovered from entry points "
                f"{previous_entry_point!r} and {entry_point.name!r}"
            )
        seen_names[manifest.name] = entry_point.name
        discovered.append(
            DiscoveredPlugin(
                manifest=manifest,
                entry_point_name=entry_point.name,
                entry_point_value=entry_point.value,
                distribution=_distribution_name(entry_point),
            )
        )
    return tuple(discovered)


def _entry_points_for_group(group: str) -> Iterable[EntryPoint]:
    all_entry_points = entry_points()
    if hasattr(all_entry_points, "select"):
        return all_entry_points.select(group=group)
    return all_entry_points.get(group, ())


def _load_entry_point(entry_point: EntryPoint) -> Any:
    try:
        return entry_point.load()
    except Exception as exc:
        raise PluginDiscoveryError(
            f"failed to load plugin entry point {entry_point.name!r}: {exc}"
        ) from exc


def _call_manifest_factory(entry_point: EntryPoint, factory: Any) -> PluginManifest:
    try:
        manifest = factory()
    except Exception as exc:
        raise PluginDiscoveryError(
            f"plugin entry point {entry_point.name!r} failed while creating "
            f"PluginManifest: {exc}"
        ) from exc
    if not isinstance(manifest, PluginManifest):
        raise PluginDiscoveryError(
            f"plugin entry point {entry_point.name!r} returned "
            f"{type(manifest).__name__}; expected PluginManifest"
        )
    return manifest


def _distribution_name(entry_point: EntryPoint) -> str | None:
    dist = getattr(entry_point, "dist", None)
    if dist is None:
        return None
    metadata = getattr(dist, "metadata", None)
    if metadata is None:
        return None
    name = metadata.get("Name")
    return str(name) if name else None
