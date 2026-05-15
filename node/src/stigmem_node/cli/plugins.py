"""Plugin inspection CLI handlers."""

from __future__ import annotations

import argparse
from typing import Any


def _load_plugin_registry() -> Any:
    from ..plugins import HookRegistry, register_discovered_plugins

    registry = HookRegistry()
    register_discovered_plugins(registry=registry)
    registry.poll_plugin_health()
    return registry


def _plugin_report_by_name(registry: Any) -> dict[str, Any]:
    return {report.plugin_name: report for report in registry.plugin_health_reports()}


def _plugin_info_to_dict(info: Any, health: Any | None = None) -> dict[str, Any]:
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
    if health is not None:
        data["health"] = {
            "status": health.status.value,
            "message": health.message,
            "checked_at": health.checked_at.isoformat(),
            "error_summary": health.error_summary,
        }
    return data


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
        print("No plugins registered")
        return 0
    for row in rows:
        health = row.get("health") or {}
        health_status = health.get("status", "unknown")
        print(
            f"{row['name']} {row['version']} "
            f"hooks={row['hook_count']} health={health_status} signed_by={row['signed_by']}"
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
