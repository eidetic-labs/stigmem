"""Compatibility shim — import from stigmem_openclaw instead."""

import stigmem_openclaw.adapter as _adapter

BootContext = _adapter.BootContext
OpenClawBootError = _adapter.OpenClawBootError
OpenClawStigmemAdapter = _adapter.OpenClawStigmemAdapter
_facts_to_summary = _adapter._facts_to_summary
_safe_assert = _adapter._safe_assert

__all__ = [
    "BootContext",
    "OpenClawBootError",
    "OpenClawStigmemAdapter",
    "_facts_to_summary",
    "_safe_assert",
]
