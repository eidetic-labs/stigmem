"""Compatibility alias for :mod:`stigmem_node.federation.federation_ingest`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "FederationHlcSkewError",
    "FederationIntegrityError",
    "ingest_fact",
    "write_audit_log",
]

if TYPE_CHECKING:
    from .federation.federation_ingest import (
        FederationHlcSkewError,
        FederationIntegrityError,
        ingest_fact,
        write_audit_log,
    )
else:
    from .federation import federation_ingest as _impl

    sys.modules[__name__] = _impl
