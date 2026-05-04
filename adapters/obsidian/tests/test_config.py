"""Unit tests for SyncConfig loader."""

from __future__ import annotations

from pathlib import Path

import pytest

from stigmem_obsidian.config import SyncConfig


def _write_config(path: Path, content: str) -> Path:
    cfg = path / ".stigmem-sync.toml"
    cfg.write_text(content, encoding="utf-8")
    return cfg


def test_load_minimal_config(tmp_path: Path) -> None:
    _write_config(tmp_path, 'node_url = "http://localhost:8765"\n')
    cfg = SyncConfig.find_and_load(tmp_path)
    assert cfg.node_url == "http://localhost:8765"
    assert cfg.scope == "local"
    assert cfg.conflict_policy == "comment"


def test_load_full_config(tmp_path: Path) -> None:
    _write_config(
        tmp_path,
        """
node_url = "http://stigmem.example.com"
vault_name = "my-vault"
api_key = "sk-test"
scope = "team"
ignored_paths = [".obsidian/**", "templates/**"]
sync_folder = "From Stigmem"
conflict_policy = "stigmem_wins"
wikilink_relation = "mentions"
watch_interval = 5.0

[[folder_scope]]
folder = "journals"
scope = "local"

[[folder_scope]]
folder = "shared"
scope = "company"
""",
    )
    cfg = SyncConfig.find_and_load(tmp_path)
    assert cfg.vault_name == "my-vault"
    assert cfg.api_key == "sk-test"
    assert cfg.scope == "team"
    assert ".obsidian/**" in cfg.ignored_paths
    assert cfg.sync_folder == "From Stigmem"
    assert cfg.conflict_policy == "stigmem_wins"
    assert cfg.wikilink_relation == "mentions"
    assert cfg.watch_interval == 5.0
    assert len(cfg.folder_scopes) == 2
    assert cfg.folder_scopes[0].folder == "journals"
    assert cfg.folder_scopes[1].scope == "company"


def test_missing_node_url_raises(tmp_path: Path) -> None:
    _write_config(tmp_path, 'vault_name = "x"\n')
    with pytest.raises(ValueError, match="node_url"):
        SyncConfig.find_and_load(tmp_path)


def test_find_config_in_parent(tmp_path: Path) -> None:
    _write_config(tmp_path, 'node_url = "http://localhost:8765"\n')
    sub = tmp_path / "notes" / "subdir"
    sub.mkdir(parents=True)
    cfg = SyncConfig.find_and_load(sub)
    assert cfg.node_url == "http://localhost:8765"


def test_no_config_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        SyncConfig.find_and_load(tmp_path)


def test_scope_for_path_folder_override(tmp_path: Path) -> None:
    cfg = SyncConfig(node_url="http://x", scope="local")
    cfg.folder_scopes = []
    from stigmem_obsidian.config import FolderScope
    cfg.folder_scopes.append(FolderScope(folder="journals", scope="team"))
    assert cfg.scope_for_path("journals/2026-05-04.md") == "team"
    assert cfg.scope_for_path("notes/other.md") == "local"


def test_is_ignored(tmp_path: Path) -> None:
    cfg = SyncConfig(node_url="http://x", ignored_paths=[".obsidian/**", "*.tmp"])
    assert cfg.is_ignored(".obsidian/workspace.json")
    assert cfg.is_ignored("foo.tmp")
    assert not cfg.is_ignored("notes/hello.md")
