"""Sliding-window per-API-key rate limiting middleware."""

from __future__ import annotations

import hashlib
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .db import db
from .settings import settings

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_WINDOW_S = 3600.0


def _key_hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def _check_and_record(key_hash: str, op_type: str, limit: int) -> tuple[bool, int]:
    """Sliding-window check and record. Returns (allowed, retry_after_seconds)."""
    now = time.time()
    window_start = now - _WINDOW_S
    with db() as conn:
        conn.execute("DELETE FROM rate_limit_buckets WHERE ts < ?", (window_start,))
        count = conn.execute(
            "SELECT COUNT(*) FROM rate_limit_buckets"
            " WHERE key_hash=? AND op_type=? AND ts>=?",
            (key_hash, op_type, window_start),
        ).fetchone()[0]
        if count >= limit:
            oldest = conn.execute(
                "SELECT MIN(ts) FROM rate_limit_buckets"
                " WHERE key_hash=? AND op_type=? AND ts>=?",
                (key_hash, op_type, window_start),
            ).fetchone()[0]
            retry_after = max(int(oldest + _WINDOW_S - now) + 1, 1)
            return False, retry_after
        conn.execute(
            "INSERT INTO rate_limit_buckets (key_hash, op_type, ts) VALUES (?,?,?)",
            (key_hash, op_type, now),
        )
        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key sliding-window rate limiting.

    Federation endpoints (/v1/federation/) are exempt — they use peer token
    auth, not user API keys. Requests without a Bearer token are also exempt.
    A limit of 0 disables rate limiting for that operation type.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith("/v1/federation/"):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            return await call_next(request)

        raw_key = auth_header[7:]
        key_hash = _key_hash(raw_key)
        op_type = "write" if request.method.upper() in _WRITE_METHODS else "read"
        limit = (
            settings.rate_limit_write_per_hour
            if op_type == "write"
            else settings.rate_limit_read_per_hour
        )

        if limit == 0:
            return await call_next(request)

        allowed, retry_after = _check_and_record(key_hash, op_type, limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
