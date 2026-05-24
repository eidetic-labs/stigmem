from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_checker():
    script_path = (
        Path(__file__).resolve().parents[3]
        / "scripts"
        / "check_tenant_resolution_consistency.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_tenant_resolution_consistency",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_source_tree_has_explicit_tenant_context_sources() -> None:
    checker = _load_checker()

    assert checker.check_paths(list(checker.DEFAULT_SCAN_ROOTS)) == []


def test_missing_tenant_context_source_is_rejected(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "from stigmem_node.plugins import TenantContext\n"
        "tenant = TenantContext(tenant_id='default')\n",
        encoding="utf-8",
    )

    failures = checker.check_paths([tmp_path])

    assert len(failures) == 1
    assert "tenant_context_source" in failures[0]


def test_federation_pin_requires_default_tenant(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "from stigmem_node.plugins import TenantContext\n"
        "tenant = TenantContext(\n"
        "    tenant_id='tenant-a',\n"
        "    metadata={'tenant_context_source': 'pinned'},\n"
        ")\n",
        encoding="utf-8",
    )

    failures = checker.check_paths([tmp_path])

    assert len(failures) == 1
    assert 'tenant_id="default"' in failures[0]


def test_explicit_hook_source_is_allowed(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "route.py"
    source.write_text(
        "from stigmem_node.plugins import TenantContext\n"
        "tenant = TenantContext(\n"
        "    tenant_id='tenant-a',\n"
        "    metadata={'tenant_context_source': 'hook'},\n"
        ")\n",
        encoding="utf-8",
    )

    assert checker.check_paths([tmp_path]) == []
