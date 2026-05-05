"""stigmem-obsidian — bidirectional sync adapter for Obsidian/Logseq/Dendron vaults."""

from .config import SyncConfig
from .syncer import VaultSyncer

__all__ = ["SyncConfig", "VaultSyncer"]
__version__ = "0.1.0"
