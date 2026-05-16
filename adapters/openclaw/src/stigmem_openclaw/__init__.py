"""stigmem-openclaw — Stigmem adapter for OpenClaw agents."""

from stigmem_openclaw.adapter import (
    SYSTEM_PROMPT_DIRECTIVE,
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
    "SYSTEM_PROMPT_DIRECTIVE",
]
