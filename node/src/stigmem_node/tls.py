"""Compatibility alias for :mod:`stigmem_node.federation.tls`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "TLS13_CIPHERS",
    "build_client_ssl_context",
    "build_server_ssl_context",
    "cert_watcher_task",
    "check_peer_san",
    "reload_tls_cert",
]

if TYPE_CHECKING:
    from .federation.tls import (
        TLS13_CIPHERS,
        build_client_ssl_context,
        build_server_ssl_context,
        cert_watcher_task,
        check_peer_san,
        reload_tls_cert,
    )
else:
    from .federation import tls as _impl

    sys.modules[__name__] = _impl
