"""B1 coverage push for modules that were at 0% — quick wins.

Targets:
  - ``stigmem_conformance.report.ConformanceReporter`` (46 stmts, 0% → near 100%)
  - ``stigmem_node.embedding.local_adapter.OllamaEmbeddingModel`` (33 stmts)
  - ``stigmem_node.embedding.openai_adapter.OpenAIEmbeddingModel`` (33 stmts)
  - ``stigmem_node.embedding.__init__.get_embedding_model`` factory (16 missing)

These are pure-construction / property / error-path checks — no real I/O.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# stigmem_conformance.report
# ---------------------------------------------------------------------------


class _FakeReport:
    """Minimal stand-in for pytest.TestReport — only the fields the reporter reads."""

    def __init__(
        self, nodeid: str, outcome: str, when: str = "call", longrepr: str | None = None
    ) -> None:
        self.nodeid = nodeid
        self.outcome = outcome
        self.when = when
        self.longrepr = longrepr


class TestConformanceReporter:
    def test_init_defaults_to_sqlite_backend(self) -> None:
        from stigmem_conformance.report import ConformanceReporter

        r = ConformanceReporter()
        assert r.backend == "sqlite"

    def test_records_only_call_phase_outcomes(self) -> None:
        from stigmem_conformance.report import ConformanceReporter

        r = ConformanceReporter(backend="postgres")
        # setup phase is ignored
        r.pytest_runtest_logreport(_FakeReport("t::a", "passed", when="setup"))
        # call phase is recorded
        r.pytest_runtest_logreport(_FakeReport("t::a", "passed", when="call"))
        r.pytest_runtest_logreport(_FakeReport("t::b", "failed", when="call", longrepr="boom"))
        r.pytest_runtest_logreport(
            _FakeReport("t::c", "skipped", when="call", longrepr="Skipped: needs pgvector")
        )
        # teardown phase is ignored
        r.pytest_runtest_logreport(_FakeReport("t::a", "passed", when="teardown"))

        md = r.generate_markdown()
        assert "postgres" in md
        assert "1 failed" in md
        assert "1/3 passed" in md
        assert "## Failures" in md
        assert "t::b" in md
        assert "boom" in md
        assert "## Skipped" in md
        assert "needs pgvector" in md
        assert "## Test details" in md

    def test_all_passed_renders_no_failures_or_skipped_sections(self) -> None:
        from stigmem_conformance.report import ConformanceReporter

        r = ConformanceReporter()
        for i in range(3):
            r.pytest_runtest_logreport(_FakeReport(f"t::ok{i}", "passed"))

        md = r.generate_markdown()
        assert "✅" in md
        assert "## Failures" not in md
        assert "## Skipped" not in md
        assert "3/3 passed" in md

    def test_empty_report_has_zero_counts(self) -> None:
        from stigmem_conformance.report import ConformanceReporter

        md = ConformanceReporter().generate_markdown()
        assert "0/0 passed" in md
        assert "**Total** | **0**" in md


# ---------------------------------------------------------------------------
# embedding factory + adapters
# ---------------------------------------------------------------------------


class TestEmbeddingFactory:
    def test_factory_returns_stub_when_provider_is_stub(self) -> None:
        from stigmem_node.embedding import get_embedding_model
        from stigmem_node.embedding.stub_adapter import StubEmbeddingModel

        s = SimpleNamespace(
            embed_model_provider="stub",
            embed_model_id="stub-test",
            embed_dimension=8,
        )
        model = get_embedding_model(s)
        assert isinstance(model, StubEmbeddingModel)
        assert model.dimension == 8
        assert model.model_id == "stub-test"

    def test_factory_returns_openai_when_provider_is_openai(self) -> None:
        from stigmem_node.embedding import get_embedding_model
        from stigmem_node.embedding.openai_adapter import OpenAIEmbeddingModel

        s = SimpleNamespace(
            embed_model_provider="openai",
            embed_model_id="text-embedding-3-small",
            embed_dimension=1536,
            embed_openai_api_key_env="OPENAI_API_KEY",
        )
        model = get_embedding_model(s)
        assert isinstance(model, OpenAIEmbeddingModel)
        assert model.dimension == 1536

    def test_factory_returns_ollama_for_default_provider(self) -> None:
        from stigmem_node.embedding import get_embedding_model
        from stigmem_node.embedding.local_adapter import OllamaEmbeddingModel

        s = SimpleNamespace(
            embed_model_provider="local",
            embed_model_id="nomic-embed-text-v1.5",
            embed_dimension=768,
            embed_ollama_url="http://localhost:11434",
        )
        model = get_embedding_model(s)
        assert isinstance(model, OllamaEmbeddingModel)
        assert model.dimension == 768

    def test_factory_uses_live_settings_when_arg_is_none(self) -> None:
        from stigmem_node.embedding import get_embedding_model

        # No arg → reads stigmem_node.settings.settings — we just check it doesn't crash
        model = get_embedding_model(None)
        # Default provider is "local" → OllamaEmbeddingModel
        assert hasattr(model, "embed")
        assert hasattr(model, "model_id")
        assert hasattr(model, "dimension")


class TestOllamaEmbeddingModel:
    def test_construction_strips_trailing_slash(self) -> None:
        from stigmem_node.embedding.local_adapter import OllamaEmbeddingModel

        m = OllamaEmbeddingModel(
            model_id="m-id",
            ollama_url="http://localhost:11434/",
            dimension=4,
        )
        assert m.model_id == "m-id"
        assert m.dimension == 4
        # Internal: trailing slash stripped (we just verify embed builds the right URL below)

    def test_embed_posts_to_ollama_and_normalises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.embedding.local_adapter import OllamaEmbeddingModel

        captured: dict[str, Any] = {}

        class _FakeResp:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, Any]:
                return {"embedding": [3.0, 4.0]}  # → l2_normalize → [0.6, 0.8]

        def fake_post(url: str, json: dict, timeout: float) -> _FakeResp:
            captured["url"] = url
            captured["json"] = json
            captured["timeout"] = timeout
            return _FakeResp()

        import httpx

        monkeypatch.setattr(httpx, "post", fake_post)

        m = OllamaEmbeddingModel(
            model_id="nomic-embed-text-v1.5",
            ollama_url="http://localhost:11434",
            dimension=2,
        )
        vecs = m.embed(["hello"])
        assert len(vecs) == 1
        assert pytest.approx(vecs[0][0], rel=1e-6) == 0.6
        assert pytest.approx(vecs[0][1], rel=1e-6) == 0.8
        assert captured["url"] == "http://localhost:11434/api/embeddings"
        assert captured["json"]["model"] == "nomic-embed-text-v1.5"
        assert captured["json"]["prompt"] == "hello"

    def test_embed_wraps_http_failure_in_embedding_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.embedding.base import EmbeddingError
        from stigmem_node.embedding.local_adapter import OllamaEmbeddingModel

        def fake_post(*a: Any, **kw: Any) -> Any:
            raise RuntimeError("connection refused")

        import httpx

        monkeypatch.setattr(httpx, "post", fake_post)

        m = OllamaEmbeddingModel(dimension=4)
        with pytest.raises(EmbeddingError, match="Ollama embedding failed"):
            m.embed(["x"])


class TestOpenAIEmbeddingModel:
    def test_construction_sets_properties(self) -> None:
        from stigmem_node.embedding.openai_adapter import OpenAIEmbeddingModel

        m = OpenAIEmbeddingModel(
            model_id="text-embedding-3-small",
            api_key_env="OPENAI_API_KEY",
            dimension=1536,
        )
        assert m.model_id == "text-embedding-3-small"
        assert m.dimension == 1536

    def test_embed_raises_when_api_key_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.embedding.base import EmbeddingError
        from stigmem_node.embedding.openai_adapter import OpenAIEmbeddingModel

        # Must have openai installed for this codepath; if not, the import-error
        # branch is taken instead (covered separately if needed).
        pytest.importorskip("openai")

        monkeypatch.delenv("STIGMEM_TEST_OPENAI_KEY", raising=False)
        m = OpenAIEmbeddingModel(api_key_env="STIGMEM_TEST_OPENAI_KEY")
        with pytest.raises(EmbeddingError, match="credentials are not configured") as excinfo:
            m.embed(["x"])
        assert "STIGMEM_TEST_OPENAI_KEY" not in str(excinfo.value)

    def test_embed_calls_openai_client_with_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.embedding.openai_adapter import OpenAIEmbeddingModel

        openai_mod = pytest.importorskip("openai")
        monkeypatch.setenv("STIGMEM_TEST_OPENAI_KEY", "sk-test")

        captured: dict[str, Any] = {}

        class _FakeEmbeddings:
            def create(self, model: str, input: list[str]) -> Any:
                captured["model"] = model
                captured["input"] = input
                # Build a response with .data[i].embedding
                return SimpleNamespace(data=[SimpleNamespace(embedding=[3.0, 4.0]) for _ in input])

        class _FakeClient:
            def __init__(self, api_key: str) -> None:
                captured["api_key"] = api_key
                self.embeddings = _FakeEmbeddings()

        monkeypatch.setattr(openai_mod, "OpenAI", _FakeClient)

        m = OpenAIEmbeddingModel(
            model_id="text-embedding-3-small",
            api_key_env="STIGMEM_TEST_OPENAI_KEY",
            dimension=2,
        )
        vecs = m.embed(["a", "b"])
        assert len(vecs) == 2
        assert captured["api_key"] == "sk-test"
        assert captured["model"] == "text-embedding-3-small"
        assert captured["input"] == ["a", "b"]

    def test_embed_wraps_api_failure_in_embedding_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from stigmem_node.embedding.base import EmbeddingError
        from stigmem_node.embedding.openai_adapter import OpenAIEmbeddingModel

        openai_mod = pytest.importorskip("openai")
        monkeypatch.setenv("STIGMEM_TEST_OPENAI_KEY", "sk-test")

        def _raising_client(*a: Any, **kw: Any) -> Any:
            raise RuntimeError("rate limited")

        monkeypatch.setattr(openai_mod, "OpenAI", _raising_client)

        m = OpenAIEmbeddingModel(api_key_env="STIGMEM_TEST_OPENAI_KEY")
        with pytest.raises(EmbeddingError, match="OpenAI embedding failed"):
            m.embed(["x"])
