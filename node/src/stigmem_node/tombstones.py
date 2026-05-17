"""Compatibility alias for :mod:`stigmem_node.lifecycle.tombstones`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "apply_inbound_revocation",
    "apply_inbound_tombstone",
    "create_tombstone",
    "filter_tombstoned_records",
    "get_tombstone_status",
    "invalidate_tombstone_cache",
    "is_tombstoned",
    "list_revocations",
    "list_tombstones",
    "revoke_tombstone",
]

if TYPE_CHECKING:
    from .lifecycle.tombstones import (
        apply_inbound_revocation,
        apply_inbound_tombstone,
        create_tombstone,
        filter_tombstoned_records,
        get_tombstone_status,
        invalidate_tombstone_cache,
        is_tombstoned,
        list_revocations,
        list_tombstones,
        revoke_tombstone,
    )
else:
    from .lifecycle import tombstones as _impl

    sys.modules[__name__] = _impl
