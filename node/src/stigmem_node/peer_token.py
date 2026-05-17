"""Compatibility alias for :mod:`stigmem_node.federation.peer_token`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "TokenError",
    "create_peer_token",
    "get_local_pubkey",
    "init_federation_keys",
    "verify_declaration_sig",
    "verify_peer_token",
]

if TYPE_CHECKING:
    from .federation.peer_token import (
        TokenError,
        create_peer_token,
        get_local_pubkey,
        init_federation_keys,
        verify_declaration_sig,
        verify_peer_token,
    )
else:
    from .federation import peer_token as _impl

    sys.modules[__name__] = _impl
