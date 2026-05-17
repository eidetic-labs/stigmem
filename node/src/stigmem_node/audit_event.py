"""Compatibility alias for :mod:`stigmem_node.observability.audit_event`."""

from __future__ import annotations

import sys

from .observability import audit_event as _impl

sys.modules[__name__] = _impl
