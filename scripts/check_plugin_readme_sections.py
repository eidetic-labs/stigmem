#!/usr/bin/env python3
"""Validate publication README sections for standalone experimental plugins."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENTAL_ROOT = REPO_ROOT / "experimental"
REQUIRED_SECTIONS = ("Installation", "Enable", "Disable", "Test", "Uninstall")


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


def missing_sections(readme: Path) -> list[str]:
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    headings = {line.removeprefix("## ").strip() for line in text.splitlines() if line.startswith("## ")}
    return [section for section in REQUIRED_SECTIONS if section not in headings]


def check_root(root: Path = DEFAULT_EXPERIMENTAL_ROOT) -> list[str]:
    failures: list[str] = []
    for pyproject in plugin_pyprojects(root):
        readme = pyproject.parent / "README.md"
        missing = missing_sections(readme)
        if missing:
            failures.append(
                f"{pyproject.parent.name}: README.md missing required section(s): "
                + ", ".join(missing)
            )
    return failures


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXPERIMENTAL_ROOT
    failures = check_root(root)
    if failures:
        print("plugin-readme-sections: failed")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"plugin-readme-sections: validated {len(plugin_pyprojects(root))} plugin README(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
