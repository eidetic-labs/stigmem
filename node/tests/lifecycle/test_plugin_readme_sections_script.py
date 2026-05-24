from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "check_plugin_readme_sections.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_plugin_readme_sections",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_plugin(root: Path, readme: str) -> None:
    plugin = root / "example-plugin"
    plugin.mkdir()
    (plugin / "pyproject.toml").write_text(
        """
[project]
name = "stigmem-plugin-example"
version = "0.9.0a8"

[project.entry-points."stigmem.plugins"]
example = "stigmem_plugin_example:plugin_manifest"
""".lstrip(),
        encoding="utf-8",
    )
    (plugin / "README.md").write_text(readme, encoding="utf-8")


def test_current_plugin_readmes_have_required_publication_sections() -> None:
    checker = _load_checker()

    assert checker.check_root() == []


def test_missing_readme_section_is_rejected(tmp_path: Path) -> None:
    checker = _load_checker()
    _write_plugin(
        tmp_path,
        "# Example\n\n## Installation\n\n## Enable\n\n## Disable\n\n## Test\n",
    )

    failures = checker.check_root(tmp_path)

    assert len(failures) == 1
    assert "Uninstall" in failures[0]


def test_all_required_sections_are_accepted(tmp_path: Path) -> None:
    checker = _load_checker()
    _write_plugin(
        tmp_path,
        "# Example\n\n## Installation\n\n## Enable\n\n## Disable\n\n## Test\n\n## Uninstall\n",
    )

    assert checker.check_root(tmp_path) == []
