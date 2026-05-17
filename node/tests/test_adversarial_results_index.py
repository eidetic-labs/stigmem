"""Tests for ADR-015 certification result index validation."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_validator() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "validate_adversarial_results.py"
    )
    spec = importlib.util.spec_from_file_location("validate_adversarial_results", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


def test_committed_certification_index_is_valid() -> None:
    assert validator.validate() == 0


def test_index_rejects_dry_run_provider_as_reviewed_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    result_path = tmp_path / "dry-run-result.json"
    result_path.write_text(
        json.dumps(
            {
                "schema_version": "adversarial-conformance-result-v1",
                "provider": "dry-run-pass",
                "model": "offline-rubric-sentinel",
                "adapter": "stigmem-offline-harness",
                "corpus": {"version": "corpus-v1"},
                "summary": {"tier": "certified"},
            }
        ),
        encoding="utf-8",
    )
    index_path = tmp_path / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema_version": "adversarial-certification-index-v1",
                "corpus_version": "corpus-v1",
                "rerun_policy": {
                    "stale_after_days": 90,
                    "triggers": ["corpus minor-version bump"],
                },
                "status_definitions": {
                    "certified": "Reviewed live result.",
                    "provisional": "Reviewed live result.",
                    "uncertified": "No reviewed live result.",
                    "expired": "Stale reviewed result.",
                    "review-needed": "Pending review.",
                },
                "reviewed_results": [
                    {
                        "provider": "dry-run-pass",
                        "model": "offline-rubric-sentinel",
                        "adapter": "stigmem-offline-harness",
                        "status": "certified",
                        "reviewed_at": "2026-05-17T00:00:00+00:00",
                        "path": str(result_path.relative_to(validator.ROOT)),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="live provider"):
        validator.validate(index_path)
