"""Unit tests for the markdown parser (no network required)."""

from __future__ import annotations

from pathlib import Path

from stigmem_obsidian.parser import (
    STIGMEM_SECTION_HEADER,
    _extract_dataview,
    _extract_wikilinks,
    _strip_code_blocks,
    add_conflict_comment,
    build_stigmem_section_body,
    extract_stigmem_section,
    parse_note,
    parse_stigmem_section_body,
    replace_stigmem_section,
)

# ---------------------------------------------------------------------------
# Wikilink extraction
# ---------------------------------------------------------------------------


def test_extract_wikilinks_simple() -> None:
    text = "See [[Alice]] and [[Bob]]."
    assert _extract_wikilinks(text) == ["Alice", "Bob"]


def test_extract_wikilinks_with_alias() -> None:
    text = "[[Project X|My Project]]"
    assert _extract_wikilinks(text) == ["Project X"]


def test_extract_wikilinks_with_heading() -> None:
    text = "[[Note#Section]]"
    assert _extract_wikilinks(text) == ["Note"]


def test_extract_wikilinks_deduplicates() -> None:
    text = "[[Alice]] and [[Alice]] again"
    assert _extract_wikilinks(text) == ["Alice"]


def test_extract_wikilinks_empty() -> None:
    assert _extract_wikilinks("No links here.") == []


# ---------------------------------------------------------------------------
# Dataview field extraction
# ---------------------------------------------------------------------------


def test_extract_dataview_basic() -> None:
    text = "status:: in-progress\nowner:: Alice"
    fields = _extract_dataview(text)
    assert fields["status"] == "in-progress"
    assert fields["owner"] == "Alice"


def test_extract_dataview_ignores_code_blocks() -> None:
    # _strip_code_blocks is applied before _extract_dataview in parse_note
    text = "```\nstatus:: should-be-ignored\n```"
    stripped = _strip_code_blocks(text)
    fields = _extract_dataview(stripped)
    assert "status" not in fields


def test_extract_dataview_empty() -> None:
    assert _extract_dataview("No dataview fields.") == {}


# ---------------------------------------------------------------------------
# parse_note integration
# ---------------------------------------------------------------------------


def test_parse_note_frontmatter(tmp_path: Path) -> None:
    note = tmp_path / "Alice.md"
    note.write_text(
        "---\ntitle: Alice Chen\ntags:\n  - engineer\naliases:\n  - alice\n---\n\nBody text.",
        encoding="utf-8",
    )
    parsed = parse_note(note, tmp_path)
    assert parsed.title == "Alice Chen"
    assert parsed.frontmatter["tags"] == ["engineer"]
    assert parsed.entity_uri == "obsidian://vault/Alice"


def test_parse_note_no_frontmatter_uses_filename(tmp_path: Path) -> None:
    note = tmp_path / "ProjectX.md"
    note.write_text("# Project X\n\nSome content.", encoding="utf-8")
    parsed = parse_note(note, tmp_path)
    assert parsed.title == "ProjectX"


def test_parse_note_wikilinks(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("See [[Alice]] and [[Bob|Robert]].", encoding="utf-8")
    parsed = parse_note(note, tmp_path)
    assert "Alice" in parsed.wikilinks
    assert "Bob" in parsed.wikilinks


def test_parse_note_dataview_fields(tmp_path: Path) -> None:
    note = tmp_path / "note.md"
    note.write_text("status:: active\npriority:: high\n", encoding="utf-8")
    parsed = parse_note(note, tmp_path)
    assert parsed.dataview_fields["status"] == "active"
    assert parsed.dataview_fields["priority"] == "high"


def test_parse_note_entity_uri_nested(tmp_path: Path) -> None:
    subdir = tmp_path / "people"
    subdir.mkdir()
    note = subdir / "Alice.md"
    note.write_text("Hello", encoding="utf-8")
    parsed = parse_note(note, tmp_path)
    assert parsed.entity_uri == "obsidian://vault/people/Alice"


def test_parse_note_content_hash_stable(tmp_path: Path) -> None:
    note = tmp_path / "stable.md"
    note.write_text("Same content.", encoding="utf-8")
    p1 = parse_note(note, tmp_path)
    p2 = parse_note(note, tmp_path)
    assert p1.content_hash == p2.content_hash


def test_parse_note_content_hash_changes(tmp_path: Path) -> None:
    note = tmp_path / "changing.md"
    note.write_text("Version 1", encoding="utf-8")
    p1 = parse_note(note, tmp_path)
    note.write_text("Version 2", encoding="utf-8")
    p2 = parse_note(note, tmp_path)
    assert p1.content_hash != p2.content_hash


# ---------------------------------------------------------------------------
# Stigmem section round-trip
# ---------------------------------------------------------------------------


def test_build_and_parse_stigmem_section_body() -> None:
    facts = [
        {"relation": "note:role", "value": "CEO", "source": "stigmem://node-1"},
        {"relation": "note:department", "value": "Engineering", "source": ""},
    ]
    body = build_stigmem_section_body(facts)
    parsed = parse_stigmem_section_body(body)
    assert parsed[0]["relation"] == "note:role"
    assert parsed[0]["value"] == "CEO"
    assert parsed[1]["relation"] == "note:department"


def test_extract_stigmem_section_present() -> None:
    content = "# Note\n\n## Stigmem\n- relation: note:role\n  value: CEO\n"
    section = extract_stigmem_section(content)
    assert section is not None
    assert "note:role" in section


def test_extract_stigmem_section_absent() -> None:
    assert extract_stigmem_section("# No stigmem section here.") is None


def test_replace_stigmem_section_update_existing() -> None:
    content = "# Note\n\n## Stigmem\n- relation: note:old\n  value: old\n"
    updated = replace_stigmem_section(content, "- relation: note:new\n  value: new")
    assert "note:new" in updated
    assert "note:old" not in updated


def test_replace_stigmem_section_append_when_absent() -> None:
    content = "# Note\n\nBody text.\n"
    updated = replace_stigmem_section(content, "- relation: note:role\n  value: CEO")
    assert STIGMEM_SECTION_HEADER in updated
    assert "note:role" in updated


def test_add_conflict_comment() -> None:
    content = "# Note\n\nBody.\n"
    updated = add_conflict_comment(content, "relation=note:role vault=CEO stigmem=CTO")
    assert "%%stigmem-conflict:" in updated
    assert "note:role" in updated
