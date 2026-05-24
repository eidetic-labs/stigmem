"""Plugin inspection CLI handlers."""

from __future__ import annotations

import argparse
import os
from typing import Any

PLUGIN_DOCS_URL = "https://docs.stigmem.dev/plugins"

KNOWN_PLUGINS: tuple[dict[str, str], ...] = (
    {
        "slug": "lazy-instruction-discovery",
        "package": "stigmem-plugin-lazy-instruction-discovery",
        "env_var": "STIGMEM_LAZY_INSTRUCTION_DISCOVERY_ENABLED",
        "summary": "Opt-in instruction manifest discovery and migration helpers.",
    },
    {
        "slug": "time-travel",
        "package": "stigmem-plugin-time-travel",
        "env_var": "STIGMEM_TIME_TRAVEL_ENABLED",
        "summary": "Opt-in historical fact and recall query behavior.",
    },
    {
        "slug": "tombstones",
        "package": "stigmem-plugin-tombstones",
        "env_var": "STIGMEM_TOMBSTONES_ENABLED",
        "summary": "Opt-in right-to-be-forgotten tombstone enforcement.",
    },
    {
        "slug": "memory-garden-acl",
        "package": "stigmem-plugin-memory-garden-acl",
        "env_var": "STIGMEM_MEMORY_GARDEN_ACL_ENABLED",
        "summary": "Opt-in memory garden membership ACL filtering.",
    },
    {
        "slug": "source-attestation",
        "package": "stigmem-plugin-source-attestation",
        "env_var": "STIGMEM_SOURCE_ATTESTATION_ENABLED",
        "summary": "Opt-in source identity checks and source-trust recall signals.",
    },
    {
        "slug": "multi-tenant",
        "package": "stigmem-plugin-multi-tenant",
        "env_var": "STIGMEM_MULTI_TENANT_ENABLED",
        "summary": "Opt-in tenant scoping and default-tenant collapse.",
    },
)


def _load_plugin_registry() -> Any:
    from ..plugins import HookRegistry, register_discovered_plugins

    registry = HookRegistry()
    register_discovered_plugins(registry=registry)
    registry.poll_plugin_health()
    return registry


def _plugin_report_by_name(registry: Any) -> dict[str, Any]:
    return {report.plugin_name: report for report in registry.plugin_health_reports()}


def _plugin_info_to_dict(info: Any, health: Any | None = None) -> dict[str, Any]:
    known = _known_plugin(info.name)
    data = {
        "name": info.name,
        "version": info.version,
        "capabilities": list(info.capabilities),
        "hooks": list(info.hooks),
        "hook_count": len(info.hooks),
        "depends_on": list(info.depends_on),
        "discovery_source": info.discovery_source,
        "signed_by": info.signed_by,
    }
    if known is not None:
        data["enabled"] = _env_enabled(known["env_var"])
        data["enable_env_var"] = known["env_var"]
    if health is not None:
        data["health"] = {
            "status": health.status.value,
            "message": health.message,
            "checked_at": health.checked_at.isoformat(),
            "error_summary": health.error_summary,
        }
    return data


def _env_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _known_plugin(name: str) -> dict[str, str] | None:
    normalized = name.removeprefix("stigmem-plugin-")
    for plugin in KNOWN_PLUGINS:
        if name in {plugin["slug"], plugin["package"]} or normalized == plugin["slug"]:
            return plugin
    return None


def _installed_plugin_names(registry: Any) -> set[str]:
    names: set[str] = set()
    for info in registry.plugin_infos():
        names.add(str(info.name))
        known = _known_plugin(str(info.name))
        if known is not None:
            names.add(known["slug"])
            names.add(known["package"])
    return names


def _plugin_doctor_rows(registry: Any) -> list[dict[str, Any]]:
    installed = _installed_plugin_names(registry)
    rows: list[dict[str, Any]] = []
    for plugin in KNOWN_PLUGINS:
        is_installed = plugin["slug"] in installed or plugin["package"] in installed
        is_enabled = _env_enabled(plugin["env_var"])
        if is_enabled and not is_installed:
            status = "enabled-not-installed"
            recommendation = f"Install {plugin['package']} or unset {plugin['env_var']}."
        elif is_installed and not is_enabled:
            status = "installed-disabled"
            recommendation = f"Set {plugin['env_var']}=1 to enable it."
        elif is_installed:
            status = "installed-enabled"
            recommendation = "No action required."
        else:
            status = "not-installed"
            recommendation = "No action required."
        rows.append(
            {
                "slug": plugin["slug"],
                "package": plugin["package"],
                "env_var": plugin["env_var"],
                "installed": is_installed,
                "enabled": is_enabled,
                "status": status,
                "recommendation": recommendation,
            }
        )
    return rows


def _print_plugin_doctor_rows(rows: list[dict[str, Any]]) -> None:
    print("Plugin state diagnostics:")
    for row in rows:
        print(
            f"{row['package']} status={row['status']} "
            f"enabled={str(row['enabled']).lower()} env={row['env_var']}"
        )
        if row["status"] in {"enabled-not-installed", "installed-disabled"}:
            print(f"  recommendation: {row['recommendation']}")
    if all(row["status"] in {"installed-enabled", "not-installed"} for row in rows):
        print("Plugin configuration looks consistent.")


def _cmd_plugins_list(args: argparse.Namespace) -> int:
    import json

    registry = _load_plugin_registry()
    infos = registry.plugin_infos()
    health_by_name = _plugin_report_by_name(registry)
    rows = [_plugin_info_to_dict(info, health_by_name.get(info.name)) for info in infos]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"No plugins registered. See {PLUGIN_DOCS_URL} for the plugin catalog.")
        return 0
    for row in rows:
        health = row.get("health") or {}
        health_status = health.get("status", "unknown")
        enabled = row.get("enabled")
        enabled_text = f" enabled={str(enabled).lower()}" if enabled is not None else ""
        print(
            f"{row['name']} {row['version']} "
            f"hooks={row['hook_count']}{enabled_text} "
            f"health={health_status} signed_by={row['signed_by']}"
        )
    return 0


def _cmd_plugins_describe(args: argparse.Namespace) -> int:
    import json
    import sys

    registry = _load_plugin_registry()
    info = registry.plugin_info(args.name)
    if info is None:
        print(f"error: plugin not found: {args.name}", file=sys.stderr)
        return 1
    health = _plugin_report_by_name(registry).get(info.name)
    data = _plugin_info_to_dict(info, health)
    if args.json:
        print(json.dumps(data, indent=2))
        return 0
    print(f"name: {data['name']}")
    print(f"version: {data['version']}")
    print(f"signed_by: {data['signed_by']}")
    print(f"capabilities: {', '.join(data['capabilities']) or '-'}")
    print(f"hooks ({data['hook_count']}): {', '.join(data['hooks']) or '-'}")
    print(f"depends_on: {', '.join(data['depends_on']) or '-'}")
    print(f"discovery_source: {json.dumps(data['discovery_source'], sort_keys=True)}")
    health_data = data.get("health") or {}
    print(f"health: {health_data.get('status', 'unknown')}")
    if health_data.get("message"):
        print(f"health_message: {health_data['message']}")
    if health_data.get("error_summary"):
        print(f"health_error: {health_data['error_summary']}")
    if health_data.get("checked_at"):
        print(f"health_checked_at: {health_data['checked_at']}")
    return 0


def _cmd_plugins_search(args: argparse.Namespace) -> int:
    import json

    query = args.query.strip().lower()
    rows = [
        plugin
        for plugin in KNOWN_PLUGINS
        if query in plugin["slug"]
        or query in plugin["package"]
        or query in plugin["summary"].lower()
    ]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    if not rows:
        print(f"No catalog matches for {args.query!r}. See {PLUGIN_DOCS_URL}.")
        return 0
    for row in rows:
        print(f"{row['package']} - {row['summary']}")
        print(f"  install: python -m pip install '{row['package']}>=0.1.0,<2.0.0'")
        print(f"  enable: export {row['env_var']}=1")
    return 0


def _cmd_plugins_enable(args: argparse.Namespace) -> int:
    plugin = _known_plugin(args.name)
    if plugin is None:
        print(f"error: unknown plugin: {args.name}")
        return 1
    print(f"python -m pip install '{plugin['package']}>=0.1.0,<2.0.0'")
    print(f"export {plugin['env_var']}=1")
    print("Restart the stigmem node after changing plugin packages or gates.")
    return 0


def _cmd_plugins_disable(args: argparse.Namespace) -> int:
    plugin = _known_plugin(args.name)
    if plugin is None:
        print(f"error: unknown plugin: {args.name}")
        return 1
    print(f"unset {plugin['env_var']}")
    print("Restart the stigmem node after changing plugin gates.")
    return 0


def _cmd_plugins_doctor(args: argparse.Namespace) -> int:
    import json

    registry = _load_plugin_registry()
    rows = _plugin_doctor_rows(registry)
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0
    _print_plugin_doctor_rows(rows)
    return 0


def _cmd_doctor(args: argparse.Namespace) -> int:
    import json

    registry = _load_plugin_registry()
    plugin_rows = _plugin_doctor_rows(registry)
    payload = {
        "status": "ok",
        "plugins": plugin_rows,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
        return 0
    print("status: ok")
    _print_plugin_doctor_rows(plugin_rows)
    return 0
