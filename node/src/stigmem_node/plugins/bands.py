"""Hook composition bands for PR 4-INF.1."""

from __future__ import annotations

from enum import IntEnum


class Band(IntEnum):
    """Deterministic hook composition tiers."""

    AUTHN = 10
    AUTHZ = 20
    VALIDATE = 30
    TRANSFORM = 40
    FILTER = 50
    RANK = 60
    PERSIST = 70
    AUDIT = 80
    OBSERVE = 90
