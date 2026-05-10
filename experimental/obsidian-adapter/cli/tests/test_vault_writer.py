"""Tests for the vault writer module."""

from __future__ import annotations

from pathlib import Path

from stigmem_obsidian.config import SyncConfig
from stigmem_obsidian.vault_writer import apply_conflict, write_facts_to_note


def _cfg(vault_root: Path) -> SyncConfig:
    return SyncConfig(node_url="http://x", sync_folder="Stigmem")


def test_write_facts_to_existing_note(tmp_path: Path) -> None:
    note = tmp_path / "Alice.md"
    note.write_text("# Alice\n\nBody.\n", encoding="utf-8")
    facts = [{"relation": "note:role", "value": "CEO", "source": "stigmem://node"}]

    modified = write_facts_to_note(tmp_path, "Alice.md", facts, _cfg(tmp_path))

    assert modified
    content = note.read_text()
    assert "## Stigmem" in content
    assert "note:role" in content
    assert "CEO" in content


def test_write_facts_no_change_when_same(tmp_path: Path) -> None:
    facts = [{"relation": "note:role", "value": "CEO", "source": "stigmem://node"}]
    from stigmem_obsidian.parser import build_stigmem_section_body, STIGMEM_SECTION_HEADER

    body = build_stigmem_section_body(facts)
    note = tmp_path / "Alice.md"
    note.write_text(f"# Alice\n\n{STIGMEM_SECTION_HEADER}\n{body}\n", encoding="utf-8")

    modified = write_facts_to_note(tmp_path, "Alice.md", facts, _cfg(tmp_path))
    assert not modified


def test_write_facts_dry_run_does_not_write(tmp_path: Path) -> None:
    note = tmp_path / "Alice.md"
    note.write_text("# Alice\n\nBody.\n", encoding="utf-8")
    original = note.read_text()
    facts = [{"relation": "note:role", "value": "CEO", "source": ""}]

    write_facts_to_note(tmp_path, "Alice.md", facts, _cfg(tmp_path), dry_run=True)

    assert note.read_text() == original


def test_create_note_for_entity(tmp_path: Path) -> None:
    facts = [
        {"relation": "note:title", "value": "New Entity", "source": "stigmem://node"},
        {"relation": "note:role", "value": "Engineer", "source": "stigmem://node"},
    ]
    cfg = _cfg(tmp_path)
    write_facts_to_note(tmp_path, "new-entity.md", facts, cfg)

    created = tmp_path / cfg.sync_folder / "new-entity.md"
    assert created.exists()
    content = created.read_text()
    assert "# New Entity" in content
    assert "note:role" in content


def test_apply_conflict_adds_comment(tmp_path: Path) -> None:
    note = tmp_path / "Alice.md"
    note.write_text("# Alice\n\nBody.\n", encoding="utf-8")

    apply_conflict(tmp_path, "Alice.md", "relation=note:role vault=CEO stigmem=CTO")

    content = note.read_text()
    assert "%%stigmem-conflict:" in content
    assert "note:role" in content


def test_apply_conflict_missing_note_skips(tmp_path: Path) -> None:
    # Should not raise
    apply_conflict(tmp_path, "nonexistent.md", "some conflict")
