"""Compatibility shim — import from stigmem_openclaw instead."""

from stigmem_openclaw.adapter import (  # noqa: F401
    BootContext,
    OpenClawStigmemAdapter,
    _facts_to_summary,
    _safe_assert,
)
