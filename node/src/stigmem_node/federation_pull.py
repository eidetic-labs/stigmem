"""Compatibility alias for :mod:`stigmem_node.federation.federation_pull`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "load_cursor",
    "save_cursor",
    "pull_from_peer_once",
    "pull_tombstones_from_peer_once",
    "pull_all_peers_once",
    "pull_loop_task",
]

if TYPE_CHECKING:
    from .federation.federation_pull import (
        load_cursor,
        pull_all_peers_once,
        pull_from_peer_once,
        pull_loop_task,
        pull_tombstones_from_peer_once,
        save_cursor,
    )
else:
    from .federation import federation_pull as _impl

    sys.modules[__name__] = _impl
