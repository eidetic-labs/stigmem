"""Vault scanner and file-watch interface."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from .config import SyncConfig
from .parser import ParsedNote, parse_note

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Vault scanner
# ---------------------------------------------------------------------------

def scan_vault(vault_root: Path, config: SyncConfig) -> list[ParsedNote]:
    """Return ParsedNote for every non-ignored markdown file in the vault."""
    notes: list[ParsedNote] = []
    for md_file in sorted(vault_root.rglob("*.md")):
        rel = str(md_file.relative_to(vault_root)).replace("\\", "/")
        if config.is_ignored(rel):
            logger.debug("scan_vault: ignoring %s", rel)
            continue
        try:
            note = parse_note(md_file, vault_root)
            notes.append(note)
        except Exception as exc:
            logger.warning("scan_vault: failed to parse %s: %s", rel, exc)
    return notes


# ---------------------------------------------------------------------------
# File watcher
# ---------------------------------------------------------------------------

class VaultWatcher:
    """Watch a vault directory for markdown changes and call *callback* on events.

    Uses watchdog's polling observer so it works on any filesystem (including
    remote vaults, Docker volumes, and network drives). Uses inotify/kqueue
    automatically on supported platforms via the default Observer.

    Callback signature: ``callback(path: Path, event_type: str) -> None``
    where event_type is one of "modified", "created", "deleted", "moved".
    """

    def __init__(
        self,
        vault_root: Path,
        config: SyncConfig,
        callback: Callable[[Path, str], None],
    ) -> None:
        self._vault_root = vault_root
        self._config = config
        self._callback = callback
        self._observer: object | None = None
        self._stop_event = threading.Event()

    def start(self) -> None:
        from watchdog.events import FileSystemEvent, FileSystemEventHandler
        from watchdog.observers import Observer

        config = self._config

        class _Handler(FileSystemEventHandler):
            def __init__(self, cb: Callable[[Path, str], None]) -> None:
                self._cb = cb

            def _handle(self, event: FileSystemEvent, event_type: str) -> None:
                if event.is_directory:
                    return
                src = Path(str(event.src_path))  # type: ignore[arg-type]
                if src.suffix != ".md":
                    return
                rel = str(src.relative_to(vault_root)).replace("\\", "/")
                if config.is_ignored(rel):
                    return
                self._cb(src, event_type)

            def on_modified(self, event: FileSystemEvent) -> None:
                self._handle(event, "modified")

            def on_created(self, event: FileSystemEvent) -> None:
                self._handle(event, "created")

            def on_deleted(self, event: FileSystemEvent) -> None:
                self._handle(event, "deleted")

            def on_moved(self, event: FileSystemEvent) -> None:
                self._handle(event, "moved")

        vault_root = self._vault_root
        observer = Observer()
        observer.schedule(_Handler(self._callback), str(vault_root), recursive=True)
        observer.start()
        self._observer = observer
        logger.info("VaultWatcher: watching %s", vault_root)

    def stop(self) -> None:
        if self._observer is not None:
            obs = self._observer  # type: ignore[attr-defined]
            obs.stop()
            obs.join()
            self._observer = None
            logger.info("VaultWatcher: stopped")

    def __enter__(self) -> "VaultWatcher":
        self.start()
        return self

    def __exit__(self, *args: object) -> None:
        self.stop()
