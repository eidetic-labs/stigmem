from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "check_admin_determination_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_admin_determination_consistency",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_source_tree_has_no_admin_proxy_patterns() -> None:
    checker = _load_checker()

    assert checker.check_paths(list(checker.DEFAULT_SCAN_ROOTS)) == []


def test_capability_combination_proxy_is_rejected(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "def require_admin(identity):\n"
        "    if identity.can_write() and identity.can_federate():\n"
        "        return True\n",
        encoding="utf-8",
    )

    failures = checker.check_paths([tmp_path])

    assert len(failures) == 1
    assert "identity.is_admin()" in failures[0]


def test_dedicated_admin_capability_is_allowed(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "def require_admin(identity):\n"
        "    if identity.is_admin():\n"
        "        return True\n",
        encoding="utf-8",
    )

    assert checker.check_paths([tmp_path]) == []


def test_direct_permissions_membership_admin_check_is_rejected(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "def require_admin(identity):\n"
        "    if \"admin\" in identity.permissions:\n"
        "        return True\n",
        encoding="utf-8",
    )

    failures = checker.check_paths([tmp_path])

    assert len(failures) == 1
    assert "identity.is_admin()" in failures[0]
