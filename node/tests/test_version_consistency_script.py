from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


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


@pytest.mark.parametrize(
    ("entry", "good_contents", "bad_contents"),
    [
        (
            {
                "id": "fastapi-app-version",
                "file": "node/src/stigmem_node/main.py",
                "pattern": r'version="(?P<version>[^"]+)"',
            },
            'app = FastAPI(version="0.9.0a1")\n',
            'app = FastAPI(version="0.9.0a2")\n',
        ),
        (
            {
                "id": "readme-status-banner",
                "file": "README.md",
                "pattern": r"^> \*\*Status: `(?P<version>v?[^`]+)`",
            },
            "> **Status: `v0.9.0a1` - active alpha**\n",
            "> **Status: `v0.9.0a2` - active alpha**\n",
        ),
        (
            {
                "id": "changelog-top-version",
                "file": "CHANGELOG.md",
                "pattern": r"^## \[(?P<version>v?0\.\d+\.\d+[abrc]?\d*)\]",
            },
            "## [0.9.0a1]\n",
            "## [0.9.0a2]\n",
        ),
        (
            {
                "id": "limitations-applies-to",
                "file": "LIMITATIONS.md",
                "pattern": r"Applies to: (?P<version>v?0\.\d+\.\d+[abrc]?\d*)",
            },
            "Applies to: v0.9.0a1\n",
            "Applies to: v0.9.0a2\n",
        ),
        (
            {
                "id": "security-applies-to",
                "file": "SECURITY.md",
                "pattern": r"^## Security Posture \u2014 (?P<version>v?0\.\d+\.\d+[abrc]?\d*)",
            },
            "## Security Posture \u2014 v0.9.0a1\n",
            "## Security Posture \u2014 v0.9.0a2\n",
        ),
        (
            {
                "id": "conformance-package-version",
                "file": "node/src/stigmem_conformance/__init__.py",
                "pattern": r'^__version__ = "(?P<version>[^"]+)"',
            },
            '__version__ = "0.9.0a1"\n',
            '__version__ = "0.9.0a2"\n',
        ),
        (
            {
                "id": "plugin-registry-fallback-version",
                "file": "node/src/stigmem_node/plugins/registry.py",
                "pattern": r'^_FALLBACK_STIGMEM_VERSION = "(?P<version>[^"]+)"',
            },
            '_FALLBACK_STIGMEM_VERSION = "0.9.0a1"\n',
            '_FALLBACK_STIGMEM_VERSION = "0.9.0a2"\n',
        ),
        (
            {
                "id": "plugin-manifest-default-requires",
                "file": "node/src/stigmem_node/plugins/manifest.py",
                "pattern": r'^    requires_stigmem: str = ">=(?P<version>[^"]+)"',
            },
            '    requires_stigmem: str = ">=0.9.0a1"\n',
            '    requires_stigmem: str = ">=0.9.0a2"\n',
        ),
        (
            {
                "id": "docusaurus-versions",
                "file": "docs/versions.json",
                "expected": [],
            },
            "[]",
            '["0.9.0a1"]',
        ),
    ],
)
def test_enforced_prose_and_runtime_surfaces_fail_on_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    entry: dict[str, object],
    good_contents: str,
    bad_contents: str,
) -> None:
    checker = _load_checker()
    monkeypatch.setattr(checker, "REPO_ROOT", tmp_path)
    surface_path = tmp_path / str(entry["file"])
    surface_path.parent.mkdir(parents=True, exist_ok=True)

    surface_path.write_text(good_contents)
    mismatches, skipped, checked = checker._check_all_surfaces(
        [entry],
        "0.9.0.alpha.1",
        False,
    )
    assert mismatches == []
    assert skipped == []
    assert checked == 1

    surface_path.write_text(bad_contents)
    mismatches, skipped, checked = checker._check_all_surfaces(
        [entry],
        "0.9.0.alpha.1",
        False,
    )
    assert skipped == []
    assert checked == 1
    assert len(mismatches) == 1
    assert mismatches[0][0] == entry["id"]


@pytest.mark.parametrize(
    "entry",
    [
        {
            "id": "stigmem-version-header",
            "kind": "internal-protocol",
            "category": "http-header",
        },
        {
            "id": "stigmem-beta-header",
            "kind": "internal-protocol",
            "category": "http-header",
        },
        {
            "id": "federation-handshake-version",
            "kind": "internal-protocol",
            "category": "protocol-handshake",
        },
        {
            "id": "rekor-manifest-version",
            "kind": "internal-build-artifact",
            "category": "transparency-log",
        },
    ],
)
def test_protocol_only_surfaces_remain_inventory_only(entry: dict[str, str]) -> None:
    checker = _load_checker()

    assert checker._entry_skip_reason(entry) == (
        f"{entry['id']} (no file/field; protocol-only)"
    )
