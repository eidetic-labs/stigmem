"""Compatibility alias for :mod:`stigmem_node.federation.peer_auth`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "PeerTokenClaims",
    "b64url_decode",
    "b64url_encode",
    "canonical_declaration_json",
    "consume_nonce",
    "get_federation_pubkey",
    "get_or_create_keypair",
    "mint_peer_token",
    "sign_declaration",
    "verify_declaration_sig",
    "verify_peer_token",
]

if TYPE_CHECKING:
    from .federation.peer_auth import (
        PeerTokenClaims,
        b64url_decode,
        b64url_encode,
        canonical_declaration_json,
        consume_nonce,
        get_federation_pubkey,
        get_or_create_keypair,
        mint_peer_token,
        sign_declaration,
        verify_declaration_sig,
        verify_peer_token,
    )
else:
    from .federation import peer_auth as _impl

    sys.modules[__name__] = _impl
