"""stigmem-openclaw — Stigmem adapter for OpenClaw agents."""

from stigmem_openclaw.adapter import (
    BootContext,
    OpenClawBootError,
    OpenClawStigmemAdapter,
    OpenClawTargetError,
    OpenClawWriteError,
    OpenClawWriteResult,
)

__all__ = [
    "OpenClawStigmemAdapter",
    "BootContext",
    "OpenClawBootError",
    "OpenClawTargetError",
    "OpenClawWriteError",
    "OpenClawWriteResult",
]
