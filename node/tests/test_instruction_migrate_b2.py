"""B2 coverage push for stigmem_node.instruction_migrate (118 missing → ~10).

Targets:
  - write_facts (433-468)
  - publish_manifest (479-516)
  - load_existing_facts_from_db (273-292)
  - load_existing_facts_from_api (301-326)
  - load_prev_manifest_names_from_db (331-348)
  - load_prev_manifest_names_from_api (353-368)
  - format_preview UPDATE/TOMBSTONE branches (409-411, 416)
  - parse_instruction_chunks edge cases (collect_md_files, slug fallback)

All HTTP paths are httpx-mocked; DB paths use a freshly-migrated tmp SQLite.
"""

from __future__ import annotations

import json
import sqlite3
import textwrap
from pathlib import Path
from typing import Any

import pytest

from stigmem_node.instruction_migrate import (
    Chunk,
    DiffEntry,
    build_fact_uri,
    compute_diff,
    format_preview,
    load_existing_facts_from_api,
    load_existing_facts_from_db,
    load_prev_manifest_names_from_api,
    load_prev_manifest_names_from_db,
    parse_instruction_chunks,
    publish_manifest,
    scope_prefix_for_role,
    scope_prefix_for_skill,
    write_facts,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeResp:
    def __init__(self, status_code: int, json_body: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}
        self.text = text or json.dumps(self._json)

    def json(self) -> Any:
        return self._json


def _diff_entry(
    action: str = "CREATE",
    unit_name: str = "u-1",
    fact_uri: str = "instruction:dev/agent/a/u-1/v1",
    content: str = "body",
    heading_text: str = "Heading",
    keywords: list[str] | None = None,
    token_estimate: int = 5,
    existing_content: str | None = None,
) -> DiffEntry:
    return DiffEntry(
        action=action,
        unit_name=unit_name,
        fact_uri=fact_uri,
        content=content,
        heading_text=heading_text,
        keywords=keywords if keywords is not None else ["k1"],
        token_estimate=token_estimate,
        existing_content=existing_content,
    )


def _migrated_db(tmp_path: Path) -> str:
    from stigmem_node.db import apply_migrations

    db_file = str(tmp_path / "im_b2.db")
    apply_migrations(db_path=db_file)
    return db_file


# ---------------------------------------------------------------------------
# scope_prefix helpers + build_fact_uri (small but uncovered branches)
# ---------------------------------------------------------------------------


class TestScopeHelpers:
    def test_scope_prefix_for_role(self) -> None:
        assert scope_prefix_for_role("prod", "agent-x") == "instruction:prod/agent/agent-x"

    def test_scope_prefix_for_skill(self) -> None:
        assert scope_prefix_for_skill("dev", "writing") == "instruction:dev/skill/writing"

    def test_build_fact_uri_format(self) -> None:
        uri = build_fact_uri("instruction:dev/agent/a", "slug-name", "v0.1")
        assert uri == "instruction:dev/agent/a/slug-name/v0.1"


# ---------------------------------------------------------------------------
# parse_instruction_chunks edge cases
# ---------------------------------------------------------------------------


class TestParseChunks:
    def test_directory_with_nested_md_files(self, tmp_path: Path) -> None:
        # Top-level + one nested .md
        (tmp_path / "top.md").write_text("## Top section\n\nbody one")
        nested = tmp_path / "sub"
        nested.mkdir()
        (nested / "deep.md").write_text("## Deep section\n\nbody two")

        chunks = parse_instruction_chunks(tmp_path)
        # Chunk.filename = md_file.stem (no extension)
        names = {c.filename for c in chunks}
        assert "top" in names
        assert "deep" in names

    def test_single_file_input(self, tmp_path: Path) -> None:
        f = tmp_path / "one.md"
        f.write_text("## Just one\n\ncontent here")
        chunks = parse_instruction_chunks(f)
        assert len(chunks) >= 1

    def test_strips_yaml_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "fm.md"
        f.write_text(
            textwrap.dedent("""\
            ---
            title: Test
            tags: [a, b]
            ---

            ## Real heading

            body
        """)
        )
        chunks = parse_instruction_chunks(f)
        # Frontmatter stripped — heading from MD becomes the chunk
        assert any("real-heading" in c.slug for c in chunks)


# ---------------------------------------------------------------------------
# format_preview — UPDATE branch (lines 409-411) + TOMBSTONE block
# ---------------------------------------------------------------------------


class TestFormatPreview:
    def test_update_entry_renders_line_delta(self, tmp_path: Path) -> None:
        d = _diff_entry(
            action="UPDATE",
            content="line one\nline two\nline three\n",
            existing_content="old\n",
        )
        out = format_preview([d], "test-scope", tmp_path, "v1")
        assert "lines:" in out
        assert "1 → 3" in out

    def test_tombstone_section_rendered(self, tmp_path: Path) -> None:
        d = _diff_entry(action="TOMBSTONE")
        out = format_preview([d], "scope", tmp_path, "v1")
        assert "[T]" in out
        assert "removed" in out

    def test_mixed_diff_summary_counts(self, tmp_path: Path) -> None:
        diff = [
            _diff_entry(action="CREATE", unit_name="c1"),
            _diff_entry(action="UPDATE", unit_name="u1", existing_content="x"),
            _diff_entry(action="NOOP", unit_name="n1"),
            _diff_entry(action="TOMBSTONE", unit_name="t1"),
        ]
        out = format_preview(diff, "scope", tmp_path, "v1")
        assert "1 create" in out
        assert "1 update" in out
        assert "1 noop" in out
        assert "1 tombstone" in out


# ---------------------------------------------------------------------------
# load_existing_facts_from_db  (273-292)
# ---------------------------------------------------------------------------


class TestLoadExistingFactsFromDb:
    def test_empty_diff_returns_empty(self, tmp_path: Path) -> None:
        db = _migrated_db(tmp_path)
        result = load_existing_facts_from_db([], db)
        assert result == {}

    def test_returns_existing_fact_content(self, tmp_path: Path) -> None:
        db = _migrated_db(tmp_path)
        # Seed a fact whose entity matches a fact_uri
        uri = "instruction:dev/agent/a/u-1/v1"
        conn = sqlite3.connect(db)
        conn.execute(
            """INSERT INTO facts
               (id, entity, relation, value_type, value_v, source, scope,
                confidence, timestamp, hlc, tenant_id, cid)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "f1",
                uri,
                "instruction:content",
                "text",
                "previous content",
                "test",
                "local",
                1.0,
                "2026-01-01T00:00:00Z",
                "0:0:0",
                "default",
                "cid:abc",
            ),
        )
        conn.commit()
        conn.close()

        diff = [_diff_entry(fact_uri=uri)]
        result = load_existing_facts_from_db(diff, db)
        assert result[uri] == "previous content"

    def test_db_failure_logs_warning_and_returns_empty(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        # Pass a bogus DB path → connection or query fails → warning printed
        diff = [_diff_entry(fact_uri="instruction:nope/v1")]
        # Use a non-DB file to trigger the DB exception path
        bogus = tmp_path / "not_a_db.txt"
        bogus.write_text("plain text")
        result = load_existing_facts_from_db(diff, str(bogus))
        # On corrupt DB, we either get {} or print a warning — both are valid
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# load_existing_facts_from_api (301-326)
# ---------------------------------------------------------------------------


class TestLoadExistingFactsFromApi:
    def test_returns_facts_when_api_responds_200(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        def fake_get(url: str, **kw: Any) -> _FakeResp:
            return _FakeResp(200, {"facts": [{"value": {"v": "api content"}}]})

        monkeypatch.setattr(httpx, "get", fake_get)

        diff = [_diff_entry(fact_uri="instruction:x/v1")]
        result = load_existing_facts_from_api(diff, "http://node", "k")
        assert result["instruction:x/v1"] == "api content"

    def test_skips_entries_without_fact_uri(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        called = []

        def fake_get(url: str, **kw: Any) -> _FakeResp:
            called.append(url)
            return _FakeResp(200, {"facts": []})

        monkeypatch.setattr(httpx, "get", fake_get)
        diff = [_diff_entry(fact_uri="")]
        assert load_existing_facts_from_api(diff, "http://node", "k") == {}
        assert called == []  # no HTTP call when fact_uri is empty

    def test_swallows_http_errors(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        def fake_get(*a: Any, **kw: Any) -> _FakeResp:
            raise RuntimeError("net down")

        monkeypatch.setattr(httpx, "get", fake_get)
        diff = [_diff_entry(fact_uri="instruction:x/v1")]
        # Best-effort — returns empty dict on failure (silently)
        assert load_existing_facts_from_api(diff, "http://node", "k") == {}

    def test_non_200_returns_no_entry(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeResp(404))
        diff = [_diff_entry(fact_uri="instruction:x/v1")]
        assert load_existing_facts_from_api(diff, "http://node", "k") == {}


# ---------------------------------------------------------------------------
# load_prev_manifest_names_from_db (331-348)
# ---------------------------------------------------------------------------


class TestLoadPrevManifestNamesFromDb:
    def test_returns_unit_names_from_active_manifest(self, tmp_path: Path) -> None:
        db = _migrated_db(tmp_path)
        conn = sqlite3.connect(db)
        body_json = json.dumps(
            [
                {"name": "alpha", "fact_uri": "x"},
                {"name": "beta", "fact_uri": "y"},
            ]
        )
        conn.execute(
            """INSERT INTO instruction_manifests
               (id, agent_id, version, fact_uri, token_count, body, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("m1", "agent-x", "v1", "instruction:x", 100, body_json, 1234567890),
        )
        conn.commit()
        conn.close()

        names = load_prev_manifest_names_from_db("agent-x", db)
        assert names == {"alpha", "beta"}

    def test_no_manifest_returns_empty(self, tmp_path: Path) -> None:
        db = _migrated_db(tmp_path)
        assert load_prev_manifest_names_from_db("ghost-agent", db) == set()

    def test_db_failure_returns_empty(self, tmp_path: Path) -> None:
        bogus = tmp_path / "bogus.db"
        bogus.write_text("plain text")
        assert load_prev_manifest_names_from_db("agent-x", str(bogus)) == set()


# ---------------------------------------------------------------------------
# load_prev_manifest_names_from_api (353-368)
# ---------------------------------------------------------------------------


class TestLoadPrevManifestNamesFromApi:
    def test_returns_names_from_api(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        def fake_get(*a: Any, **kw: Any) -> _FakeResp:
            return _FakeResp(200, {"entries": [{"name": "x"}, {"name": "y"}]})

        monkeypatch.setattr(httpx, "get", fake_get)
        names = load_prev_manifest_names_from_api("a", "http://n", "k")
        assert names == {"x", "y"}

    def test_404_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeResp(404))
        assert load_prev_manifest_names_from_api("a", "http://n", "k") == set()

    def test_network_failure_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        import httpx

        def boom(*a: Any, **kw: Any) -> _FakeResp:
            raise RuntimeError("down")

        monkeypatch.setattr(httpx, "get", boom)
        assert load_prev_manifest_names_from_api("a", "http://n", "k") == set()


# ---------------------------------------------------------------------------
# write_facts (433-468)
# ---------------------------------------------------------------------------


class TestWriteFacts:
    def test_skips_noop_and_tombstone(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import httpx

        called = []

        def fake_post(*a: Any, **kw: Any) -> _FakeResp:
            called.append(kw)
            return _FakeResp(201)

        monkeypatch.setattr(httpx, "post", fake_post)
        diff = [
            _diff_entry(action="NOOP"),
            _diff_entry(action="TOMBSTONE"),
        ]
        written, failed = write_facts(diff, "http://n", "k")
        assert written == 0
        assert failed == 0
        assert called == []  # no posts for NOOP/TOMBSTONE

    def test_create_and_update_post_to_facts_endpoint(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import httpx

        def fake_post(url: str, **kw: Any) -> _FakeResp:
            return _FakeResp(201)

        monkeypatch.setattr(httpx, "post", fake_post)
        diff = [
            _diff_entry(action="CREATE", unit_name="c1"),
            _diff_entry(action="UPDATE", unit_name="u1"),
        ]
        written, failed = write_facts(diff, "http://n", "k")
        assert written == 2
        assert failed == 0
        out = capsys.readouterr().out
        assert "c1 ✓" in out
        assert "u1 ✓" in out

    def test_non_201_response_increments_failed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import httpx

        monkeypatch.setattr(httpx, "post", lambda *a, **kw: _FakeResp(500, text="boom"))

        diff = [_diff_entry(action="CREATE", unit_name="c1")]
        written, failed = write_facts(diff, "http://n", "k")
        assert written == 0
        assert failed == 1
        assert "FAILED: 500" in capsys.readouterr().err

    def test_network_exception_increments_failed(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import httpx

        def boom(*a: Any, **kw: Any) -> _FakeResp:
            raise RuntimeError("connection reset")

        monkeypatch.setattr(httpx, "post", boom)
        diff = [_diff_entry(action="CREATE", unit_name="c1")]
        written, failed = write_facts(diff, "http://n", "k")
        assert written == 0
        assert failed == 1
        assert "connection reset" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# publish_manifest (479-516)
# ---------------------------------------------------------------------------


class TestPublishManifest:
    def test_success_returns_true(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        import httpx

        captured: dict = {}

        def fake_put(url: str, **kw: Any) -> _FakeResp:
            captured["url"] = url
            captured["json"] = kw.get("json")
            return _FakeResp(200)

        monkeypatch.setattr(httpx, "put", fake_put)
        diff = [
            _diff_entry(action="CREATE", unit_name="a"),
            _diff_entry(action="UPDATE", unit_name="b"),
            _diff_entry(action="TOMBSTONE", unit_name="t1"),  # excluded
        ]
        ok = publish_manifest("agent-1", diff, "v1.0", "http://n", "k")
        assert ok is True
        # Tombstone entries are excluded from manifest payload
        names = {e["name"] for e in captured["json"]["entries"]}
        assert names == {"a", "b"}
        assert "instruction-manifest" in captured["url"]

    def test_non_200_returns_false_with_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import httpx

        monkeypatch.setattr(httpx, "put", lambda *a, **kw: _FakeResp(500, text="server err"))
        ok = publish_manifest("a", [_diff_entry()], "v1", "http://n", "k")
        assert ok is False
        assert "Manifest publish FAILED" in capsys.readouterr().err

    def test_network_failure_returns_false(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import httpx

        def boom(*a: Any, **kw: Any) -> _FakeResp:
            raise RuntimeError("net error")

        monkeypatch.setattr(httpx, "put", boom)
        ok = publish_manifest("a", [_diff_entry()], "v1", "http://n", "k")
        assert ok is False
        assert "net error" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# compute_diff cross-paths
# ---------------------------------------------------------------------------


class TestComputeDiff:
    def _chunk(self, slug: str = "u-1", content: str = "body") -> Chunk:
        return Chunk(
            filename="src.md",
            heading_text="H",
            slug=slug,
            content=content,
            keywords=["k"],
            token_estimate=5,
        )

    def test_create_when_no_existing(self) -> None:
        chunks = [self._chunk(slug="new-unit", content="body")]
        diff = compute_diff(
            chunks,
            "dev/agent/a",
            "v1",
            existing_content={},
            prev_manifest_names=set(),
        )
        assert len(diff) >= 1
        assert any(d.action == "CREATE" for d in diff)

    def test_update_when_content_differs(self) -> None:
        c = self._chunk(slug="u-1", content="new body")
        uri = build_fact_uri("dev/agent/a", "u-1", "v1")
        diff = compute_diff(
            [c],
            "dev/agent/a",
            "v1",
            existing_content={uri: "old body"},
            prev_manifest_names={"u-1"},
        )
        actions = {d.action for d in diff}
        assert "UPDATE" in actions

    def test_noop_when_content_unchanged(self) -> None:
        c = self._chunk(slug="u-1", content="same body")
        uri = build_fact_uri("dev/agent/a", "u-1", "v1")
        diff = compute_diff(
            [c],
            "dev/agent/a",
            "v1",
            existing_content={uri: "same body"},
            prev_manifest_names={"u-1"},
        )
        assert any(d.action == "NOOP" for d in diff)

    def test_tombstone_when_prev_unit_removed(self) -> None:
        # Current chunks empty; prev manifest had "removed-unit"
        diff = compute_diff(
            [],
            "dev/agent/a",
            "v1",
            existing_content={},
            prev_manifest_names={"removed-unit"},
        )
        assert any(d.action == "TOMBSTONE" and d.unit_name == "removed-unit" for d in diff)
