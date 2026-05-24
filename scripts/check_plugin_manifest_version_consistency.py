#!/usr/bin/env python3
"""Validate standalone plugin manifest versions match pyproject versions."""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENTAL_ROOT = REPO_ROOT / "experimental"


def plugin_pyprojects(root: Path = DEFAULT_EXPERIMENTAL_ROOT) -> list[Path]:
    """Return pyprojects for standalone stigmem-plugin-* packages."""
    projects: list[Path] = []
    for pyproject in sorted(root.glob("*/pyproject.toml")):
        with pyproject.open("rb") as handle:
            data = tomllib.load(handle)
        name = data.get("project", {}).get("name", "")
        entry_points = data.get("project", {}).get("entry-points", {})
        if name.startswith("stigmem-plugin-") and "stigmem.plugins" in entry_points:
            projects.append(pyproject)
    return projects


def pyproject_version(pyproject: Path) -> str:
    with pyproject.open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def manifest_version(manifest: Path) -> str | None:
    tree = ast.parse(manifest.read_text(encoding="utf-8"), filename=str(manifest))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if "PLUGIN_VERSION" in names and isinstance(node.value, ast.Constant):
                return str(node.value.value)
    return None


def manifest_paths(plugin_root: Path) -> list[Path]:
    return sorted(plugin_root.glob("src/stigmem_plugin_*/manifest.py"))


def check_root(root: Path = DEFAULT_EXPERIMENTAL_ROOT) -> list[str]:
    failures: list[str] = []
    for pyproject in plugin_pyprojects(root):
        expected = pyproject_version(pyproject)
        manifests = manifest_paths(pyproject.parent)
        if not manifests:
            failures.append(f"{pyproject.parent.name}: no manifest.py found")
            continue
        for manifest in manifests:
            actual = manifest_version(manifest)
            if actual != expected:
                failures.append(
                    f"{pyproject.parent.name}: {manifest.relative_to(pyproject.parent)} "
                    f"PLUGIN_VERSION={actual!r}, pyproject version={expected!r}"
                )
    return failures


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXPERIMENTAL_ROOT
    failures = check_root(root)
    if failures:
        print("plugin-manifest-version-consistency: failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(
        "plugin-manifest-version-consistency: "
        f"validated {len(plugin_pyprojects(root))} plugin manifest(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
