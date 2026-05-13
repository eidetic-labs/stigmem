from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_checker():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "check_version_consistency.py"
    spec = importlib.util.spec_from_file_location("check_version_consistency", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_extract_pattern_reads_named_version_group(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "main.py"
    source.write_text('app = FastAPI(version="0.9.0a1")\n')

    assert (
        checker.extract_pattern(source, r'version="(?P<version>[^"]+)"')
        == "0.9.0a1"
    )


def test_extract_literal_reads_json_metadata(tmp_path: Path) -> None:
    checker = _load_checker()
    source = tmp_path / "versions.json"
    source.write_text(json.dumps([]))

    assert checker.extract_literal(source) == []


def test_markdown_pattern_surface_is_checked_not_skipped() -> None:
    checker = _load_checker()
    entry = {
        "id": "readme-status-banner",
        "kind": "documentation",
        "category": "prose",
        "file": "README.md",
        "pattern": r"irrelevant",
        "spelling": "shorthand",
        "sort_authority": "pep440",
    }

    assert checker._entry_skip_reason(entry) is None
