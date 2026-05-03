"""Stigmem client exceptions."""

from __future__ import annotations


class StigmemError(Exception):
    """Base exception for all stigmem client errors."""


class StigmemHTTPError(StigmemError):
    """An HTTP error response from the stigmem node."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"HTTP {status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail


class StigmemAuthError(StigmemHTTPError):
    """401/403 from the node."""


class StigmemNotFoundError(StigmemHTTPError):
    """404 from the node."""


class StigmemConflictError(StigmemHTTPError):
    """409 from the node (e.g. duplicate peer)."""
