"""Tenant identifier validation and normalization helpers."""

from __future__ import annotations

import re
import unicodedata

DEFAULT_TENANT_ID = "default"
TENANT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class TenantIdError(ValueError):
    """Raised when a tenant identifier fails validation."""


def validate_tenant_id(value: str | None) -> str:
    """Normalize and validate a tenant identifier.

    Tenant IDs are NFKC-normalized, stripped, lowercased, and then restricted
    to 1-63 URL-safe characters: lowercase ASCII alphanumerics plus hyphen,
    starting with an alphanumeric character.
    """

    if value is None:
        raise TenantIdError("tenant_id_empty")
    normalized = unicodedata.normalize("NFKC", str(value)).strip().lower()
    if not normalized:
        raise TenantIdError("tenant_id_empty")
    if not TENANT_ID_PATTERN.fullmatch(normalized):
        raise TenantIdError(f"tenant_id_invalid: {value!r}")
    return normalized
