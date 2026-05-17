"""Compatibility alias for :mod:`stigmem_node.observability.audit_event`."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

__all__ = [
    "INSTRUCTION_PROMOTED",
    "INSTRUCTION_QUARANTINED",
    "emit",
    "emit_instruction_event_if_applicable",
    "emit_nofail",
    "is_instruction_fact",
]

if TYPE_CHECKING:
    from .observability.audit_event import (
        INSTRUCTION_PROMOTED,
        INSTRUCTION_QUARANTINED,
        emit,
        emit_instruction_event_if_applicable,
        emit_nofail,
        is_instruction_fact,
    )
else:
    from .observability import audit_event as _impl

    sys.modules[__name__] = _impl
