"""Hybrid Logical Clock — spec §2.4.

One global HLC instance per node process. Thread-safe.

Format: "{wall_ms_utc}.{counter}"  e.g. "1746230400000.003"
"""

from __future__ import annotations

import threading
import time


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

    def receive(self, remote: str) -> str:
        """Advance on receiving a federated fact (§2.4 rule 2)."""
        r_wall, r_ctr = _parse(remote)
        with self._lock:
            now = int(time.time() * 1000)
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
