from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


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


def test_mcp_readme_consistency_script_catches_http_route_drift(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script_path = (
        Path(__file__).resolve().parents[3] / "scripts" / "check_mcp_readme_consistency.py"
    )
    spec = importlib.util.spec_from_file_location("check_mcp_readme_consistency", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setattr(module, "_http_route_editors", lambda: {"codex-cli", "extra-editor"})

    assert module.main() == 1
    assert "/v1/mcp/connectors" in capsys.readouterr().out
