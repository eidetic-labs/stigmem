"""Configuration loader for .stigmem-sync.toml."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib  # type: ignore[no-redef]


@dataclass
class FolderScope:
    """Maps a vault folder path prefix to a stigmem scope."""

    folder: str
    scope: str = "local"
    relation_prefix: str = "note"


@dataclass
class SyncConfig:
    """Parsed .stigmem-sync.toml configuration."""

    # Required
    node_url: str

    # Optional identity
    vault_name: str = "vault"
    api_key: str | None = None

    # Sync behaviour
    scope: str = "local"
    ignored_paths: list[str] = field(default_factory=list)
    sync_folder: str = "Stigmem"

    # Per-folder scope overrides (list of FolderScope)
    folder_scopes: list[FolderScope] = field(default_factory=list)

    # Conflict policy: "stigmem_wins" | "vault_wins" | "comment"
    conflict_policy: str = "comment"

    # Wikilink relation (default "references", override per tag via tag_relations)
    wikilink_relation: str = "references"
    tag_relations: dict[str, str] = field(default_factory=dict)

    # Watch mode poll interval (seconds)
    watch_interval: float = 2.0

    @classmethod
    def from_toml(cls, path: Path) -> "SyncConfig":
        """Load config from a .stigmem-sync.toml file."""
        with open(path, "rb") as f:
            raw = tomllib.load(f)

        node_url = raw.get("node_url", "")
        if not node_url:
            raise ValueError(f"node_url is required in {path}")

        folder_scopes: list[FolderScope] = []
        for fs in raw.get("folder_scope", []):
            folder_scopes.append(
                FolderScope(
                    folder=fs["folder"],
                    scope=fs.get("scope", "local"),
                    relation_prefix=fs.get("relation_prefix", "note"),
                )
            )

        return cls(
            node_url=node_url,
            vault_name=raw.get("vault_name", "vault"),
            api_key=raw.get("api_key"),
            scope=raw.get("scope", "local"),
            ignored_paths=raw.get("ignored_paths", []),
            sync_folder=raw.get("sync_folder", "Stigmem"),
            folder_scopes=folder_scopes,
            conflict_policy=raw.get("conflict_policy", "comment"),
            wikilink_relation=raw.get("wikilink_relation", "references"),
            tag_relations=raw.get("tag_relations", {}),
            watch_interval=float(raw.get("watch_interval", 2.0)),
        )

    @classmethod
    def find_and_load(cls, vault_path: Path) -> "SyncConfig":
        """Search vault_path and parents for .stigmem-sync.toml and load it."""
        for candidate in [vault_path, *vault_path.parents]:
            cfg_file = candidate / ".stigmem-sync.toml"
            if cfg_file.exists():
                return cls.from_toml(cfg_file)
        raise FileNotFoundError(
            f"No .stigmem-sync.toml found in {vault_path} or any parent directory"
        )

    def scope_for_path(self, rel_path: str) -> str:
        """Return the effective stigmem scope for a vault-relative path."""
        for fs in self.folder_scopes:
            if rel_path.startswith(fs.folder):
                return fs.scope
        return self.scope

    def is_ignored(self, rel_path: str) -> bool:
        """Return True if the path matches any ignored_paths glob pattern."""
        from fnmatch import fnmatch
        return any(fnmatch(rel_path, pat) for pat in self.ignored_paths)
