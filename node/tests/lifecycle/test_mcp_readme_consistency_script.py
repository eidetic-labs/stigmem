from __future__ import annotations

import importlib.util
from pathlib import Path


def test_mcp_readme_consistency_script_passes() -> None:
    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "check_mcp_readme_consistency.py"
    )
    spec = importlib.util.spec_from_file_location("check_mcp_readme_consistency", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.main() == 0
