"""Tests for the ADR-015 adversarial conformance runner."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest


def _load_runner() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "run_adversarial_conformance.py"
    )
    spec = importlib.util.spec_from_file_location("run_adversarial_conformance", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_load_corpus_reads_all_seed_patterns() -> None:
    corpus = runner.load_corpus()

    assert corpus.version == "corpus-v1"
    assert len(corpus.categories) == 10
    assert len(corpus.patterns) == 80
    assert {pattern.severity for pattern in corpus.patterns} <= {
        "critical",
        "high",
        "medium",
        "low",
    }


def test_dry_run_pass_provider_produces_certified_summary() -> None:
    corpus = runner.load_corpus()
    results = runner.run_corpus(corpus, runner.dry_run_pass_provider)
    summary = runner.summarize(corpus, results)

    assert summary["total"] == 80
    assert summary["fail"] == 0
    assert summary["review_needed"] == 0
    assert summary["overall_pass_rate"] == 1.0
    assert summary["critical_high_pass_rate"] == 1.0
    assert summary["tier"] == "certified"


def test_fail_and_review_outcomes_affect_tier() -> None:
    corpus = runner.load_corpus()

    fail_summary = runner.summarize(
        corpus,
        runner.run_corpus(corpus, runner.dry_run_fail_provider),
    )
    review_summary = runner.summarize(
        corpus,
        runner.run_corpus(corpus, runner.dry_run_review_provider),
    )

    assert fail_summary["tier"] == "uncertified"
    assert fail_summary["fail"] == 80
    assert review_summary["tier"] == "uncertified"
    assert review_summary["review_needed"] == 80


def test_result_document_and_write_output(tmp_path: Path) -> None:
    corpus = runner.load_corpus()
    results = runner.run_corpus(corpus, runner.dry_run_pass_provider)
    document = runner.result_document(
        corpus=corpus,
        results=results,
        provider_name="dry-run-pass",
        model="offline-test",
        adapter="stigmem-offline-harness",
        generated_at=runner.datetime(2026, 5, 16, 12, 30, tzinfo=runner.UTC),
    )
    output = tmp_path / "result.json"

    runner.write_result(document, output)
    parsed = json.loads(output.read_text(encoding="utf-8"))

    assert parsed["schema_version"] == "adversarial-conformance-result-v1"
    assert parsed["generated_at"] == "2026-05-16T12:30:00+00:00"
    assert parsed["summary"]["tier"] == "certified"
    assert parsed["patterns"][0]["outcome"] == "pass"


def test_cli_writes_result_and_sets_exit_code(tmp_path: Path) -> None:
    output = tmp_path / "cli-result.json"

    ok_exit = runner.main(
        [
            "--provider",
            "dry-run-pass",
            "--model",
            "offline cli",
            "--output",
            str(output),
        ]
    )
    fail_exit = runner.main(
        [
            "--provider",
            "dry-run-fail",
            "--output",
            str(tmp_path / "fail-result.json"),
        ]
    )

    assert ok_exit == 0
    assert output.exists()
    assert fail_exit == 1


def test_unknown_provider_is_explicitly_unsupported() -> None:
    with pytest.raises(ValueError, match="not implemented"):
        runner.build_provider("openai")
