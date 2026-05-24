from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "check_plugin_readme_pypi_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_plugin_readme_pypi_consistency",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_plugin_catalog_surfaces_are_consistent() -> None:
    checker = _load_checker()

    assert checker.check_readme() == []
    assert checker.check_pyproject_extras() == []
    assert checker.check_docs_catalog() == []
