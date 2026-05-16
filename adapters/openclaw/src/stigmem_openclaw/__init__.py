"""stigmem-openclaw — Stigmem adapter for OpenClaw agents."""

from stigmem_openclaw.adapter import (
    BootContext,
    OpenClawBootError,
    OpenClawStigmemAdapter,
    OpenClawTargetError,
)

__all__ = [
    "OpenClawStigmemAdapter",
    "BootContext",
    "OpenClawBootError",
    "OpenClawTargetError",
]
