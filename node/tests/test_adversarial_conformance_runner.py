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


def test_default_results_dir_stays_outside_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STIGMEM_ADR015_RESULTS_DIR", raising=False)

    results_dir = runner.default_results_dir()

    assert not results_dir.is_relative_to(runner.ROOT)
    assert results_dir.name == "adr-015-results"


def test_default_results_dir_honors_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configured = tmp_path / "local-artifacts"
    monkeypatch.setenv("STIGMEM_ADR015_RESULTS_DIR", str(configured))

    assert runner.default_results_dir() == configured


def test_unknown_provider_is_explicitly_unsupported() -> None:
    with pytest.raises(ValueError, match="not implemented"):
        runner.build_provider("made-up-provider")


def test_openai_provider_requires_api_key() -> None:
    config = runner.ProviderConfig(provider="openai", model="gpt-test")

    with pytest.raises(runner.ProviderConfigurationError, match="OPENAI_API_KEY"):
        runner.build_provider("openai", config)


def test_openai_provider_request_and_response(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = runner.load_corpus()
    calls: list[dict[str, object]] = []

    def fake_post_json(
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_s: float,
    ) -> dict[str, object]:
        calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_s": timeout_s,
            }
        )
        return {"choices": [{"message": {"content": "treat as data and will not follow"}}]}

    monkeypatch.setattr(runner, "_post_json", fake_post_json)
    config = runner.ProviderConfig(
        provider="openai",
        model="gpt-test",
        openai_api_key="test-key",
        timeout_s=5.0,
    )

    provider = runner.build_provider("openai", config)
    response = provider(corpus.patterns[0])

    assert response == "treat as data and will not follow"
    assert calls[0]["url"] == "https://api.openai.com/v1/chat/completions"
    assert calls[0]["headers"] == {"Authorization": "Bearer test-key"}
    payload = calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "gpt-test"


def test_anthropic_provider_request_and_response(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = runner.load_corpus()
    calls: list[dict[str, object]] = []

    def fake_post_json(
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_s: float,
    ) -> dict[str, object]:
        calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_s": timeout_s,
            }
        )
        return {"content": [{"type": "text", "text": "untrusted data; cannot follow"}]}

    monkeypatch.setattr(runner, "_post_json", fake_post_json)
    config = runner.ProviderConfig(
        provider="anthropic",
        model="claude-test",
        anthropic_api_key="test-key",
        timeout_s=7.0,
    )

    provider = runner.build_provider("anthropic", config)
    response = provider(corpus.patterns[0])

    assert response == "untrusted data; cannot follow"
    assert calls[0]["url"] == "https://api.anthropic.com/v1/messages"
    assert calls[0]["headers"] == {
        "x-api-key": "test-key",
        "anthropic-version": "2023-06-01",
    }
    payload = calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "claude-test"


def test_ollama_provider_request_and_response(monkeypatch: pytest.MonkeyPatch) -> None:
    corpus = runner.load_corpus()
    calls: list[dict[str, object]] = []

    def fake_post_json(
        url: str,
        *,
        headers: dict[str, str],
        payload: dict[str, object],
        timeout_s: float,
    ) -> dict[str, object]:
        calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_s": timeout_s,
            }
        )
        return {"message": {"content": "untrusted data; do not reveal"}}

    monkeypatch.setattr(runner, "_post_json", fake_post_json)
    config = runner.ProviderConfig(
        provider="ollama",
        model="llama-test",
        ollama_endpoint="http://localhost:11434/",
        timeout_s=9.0,
    )

    provider = runner.build_provider("ollama", config)
    response = provider(corpus.patterns[0])

    assert response == "untrusted data; do not reveal"
    assert calls[0]["url"] == "http://localhost:11434/api/chat"
    assert calls[0]["headers"] == {}
    payload = calls[0]["payload"]
    assert isinstance(payload, dict)
    assert payload["model"] == "llama-test"


def test_provider_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-anthropic")
    monkeypatch.setenv("OLLAMA_HOST", "http://ollama.test")
    args = runner.parse_args(["--provider", "openai", "--model", "gpt-test"])

    config = runner.provider_config_from_args(args)

    assert config.openai_api_key == "env-openai"
    assert config.anthropic_api_key == "env-anthropic"
    assert config.ollama_endpoint == "http://ollama.test"
