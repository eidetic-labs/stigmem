"""Compatibility alias for :mod:`stigmem_node.lifecycle.tombstone_signing`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "get_node_key_id",
    "sign_revocation",
    "sign_tombstone",
    "verify_revocation_signature",
    "verify_tombstone_signature",
]

if TYPE_CHECKING:
    from .lifecycle.tombstone_signing import (
        get_node_key_id,
        sign_revocation,
        sign_tombstone,
        verify_revocation_signature,
        verify_tombstone_signature,
    )
else:
    from .lifecycle import tombstone_signing as _impl

    sys.modules[__name__] = _impl
