from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "check_plugin_manifest_version_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_plugin_manifest_version_consistency",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write_plugin(root: Path, *, pyproject_version: str, manifest_version: str) -> None:
    plugin = root / "example-plugin"
    package = plugin / "src" / "stigmem_plugin_example"
    package.mkdir(parents=True)
    (plugin / "pyproject.toml").write_text(
        f"""
[project]
name = "stigmem-plugin-example"
version = "{pyproject_version}"

[project.entry-points."stigmem.plugins"]
example = "stigmem_plugin_example:plugin_manifest"
""".lstrip(),
        encoding="utf-8",
    )
    (package / "manifest.py").write_text(
        f'PLUGIN_VERSION = "{manifest_version}"\n',
        encoding="utf-8",
    )


def test_current_plugin_manifests_match_pyproject_versions() -> None:
    checker = _load_checker()

    assert checker.check_root() == []


def test_manifest_version_drift_is_rejected(tmp_path: Path) -> None:
    checker = _load_checker()
    _write_plugin(tmp_path, pyproject_version="0.9.0a8", manifest_version="0.1.0")

    failures = checker.check_root(tmp_path)

    assert len(failures) == 1
    assert "PLUGIN_VERSION='0.1.0'" in failures[0]
    assert "pyproject version='0.9.0a8'" in failures[0]


def test_matching_manifest_version_is_accepted(tmp_path: Path) -> None:
    checker = _load_checker()
    _write_plugin(tmp_path, pyproject_version="0.9.0a8", manifest_version="0.9.0a8")

    assert checker.check_root(tmp_path) == []
