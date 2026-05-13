"""Hybrid Logical Clock — spec §2.4.

One global HLC instance per node process. Thread-safe.

Format: "{wall_ms_utc}.{counter}"  e.g. "1746230400000.003"
"""

from __future__ import annotations

import threading
import time


class HLCRemoteSkewError(ValueError):
    """Remote HLC wall time is outside the configured federation skew bound."""

    def __init__(
        self,
        *,
        remote_wall_ms: int,
        local_wall_ms: int,
        max_future_skew_ms: int,
        max_past_skew_ms: int,
    ) -> None:
        self.remote_wall_ms = remote_wall_ms
        self.local_wall_ms = local_wall_ms
        self.max_future_skew_ms = max_future_skew_ms
        self.max_past_skew_ms = max_past_skew_ms
        self.skew_ms = remote_wall_ms - local_wall_ms
        if self.skew_ms > max_future_skew_ms:
            self.direction = "future"
        else:
            self.direction = "past"
        super().__init__(
            "remote HLC wall time is outside configured skew bound "
            f"(direction={self.direction}, skew_ms={self.skew_ms})"
        )


def _parse(s: str) -> tuple[int, int]:
    parts = s.split(".", 1)
    return int(parts[0]), int(parts[1]) if len(parts) > 1 else 0


class HLC:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._wall_ms: int = 0
        self._counter: int = 0

    def tick(self) -> str:
        """Advance on local write (§2.4 rule 1)."""
        with self._lock:
            now = int(time.time() * 1000)
            if now > self._wall_ms:
                self._wall_ms = now
                self._counter = 0
            else:
                self._counter += 1
            return f"{self._wall_ms}.{self._counter}"

    def receive(
        self,
        remote: str,
        *,
        max_future_skew_ms: int | None = None,
        max_past_skew_ms: int | None = None,
    ) -> str:
        """Advance on receiving a federated fact (§2.4 rule 2)."""
        r_wall, r_ctr = _parse(remote)
        with self._lock:
            now = int(time.time() * 1000)
            future_limit = max_future_skew_ms if max_future_skew_ms is not None else 0
            past_limit = max_past_skew_ms if max_past_skew_ms is not None else 0
            if future_limit > 0 and r_wall - now > future_limit:
                raise HLCRemoteSkewError(
                    remote_wall_ms=r_wall,
                    local_wall_ms=now,
                    max_future_skew_ms=future_limit,
                    max_past_skew_ms=past_limit,
                )
            if past_limit > 0 and now - r_wall > past_limit:
                raise HLCRemoteSkewError(
                    remote_wall_ms=r_wall,
                    local_wall_ms=now,
                    max_future_skew_ms=future_limit,
                    max_past_skew_ms=past_limit,
                )
            new_wall = max(now, self._wall_ms, r_wall)
            if new_wall == self._wall_ms == r_wall:
                self._counter = max(self._counter, r_ctr) + 1
            elif new_wall == self._wall_ms:
                self._counter += 1
            elif new_wall == r_wall:
                self._counter = r_ctr + 1
            else:
                self._counter = 0
            self._wall_ms = new_wall
            return f"{self._wall_ms}.{self._counter}"

    @staticmethod
    def compare(a: str, b: str) -> int:
        """Causal ordering: returns -1, 0, or 1."""
        at = _parse(a)
        bt = _parse(b)
        if at < bt:
            return -1
        if at > bt:
            return 1
        return 0


node_hlc = HLC()
