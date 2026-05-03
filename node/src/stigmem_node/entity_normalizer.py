"""Entity URI normalization — spec §2.6 (v0.7 normative).

Strict normalizer: deterministic, idempotent, no alias resolution.
Full fuzzy resolver (Kompl-style) is Phase 6.
"""

from __future__ import annotations

import re

_FORMAL_URI_RE = re.compile(r"^stigmem://([^/]+)/([^/]+)/(.+)$")
_WHITESPACE_RE = re.compile(r"\s+")


class NormalizationError(ValueError):
    pass


def normalize_entity_uri(raw: str) -> str:
    """Return the canonical form of an entity URI string.

    For formal URIs (stigmem://authority/type/id): lowercases authority, type,
    and id; trims surrounding whitespace; collapses whitespace in id to hyphens.

    For informal URIs (type:id, type/id, bare id): lowercases the entire string
    and collapses whitespace to hyphens without changing the URI format.
    Does NOT convert informal to formal (that is a separate migration concern).

    Raises NormalizationError on empty or whitespace-only input.
    """
    if not raw or not raw.strip():
        raise NormalizationError("entity URI must not be empty")

    stripped = raw.strip()
    m = _FORMAL_URI_RE.match(stripped)
    if m:
        authority = m.group(1).strip().lower()
        type_slug = m.group(2).strip().lower()
        id_part = _WHITESPACE_RE.sub("-", m.group(3).strip().lower())
        if not authority or not type_slug or not id_part:
            raise NormalizationError(
                f"normalization produced empty component in formal URI: {raw!r}"
            )
        return f"stigmem://{authority}/{type_slug}/{id_part}"

    # Informal URI: lowercase and collapse whitespace
    return _WHITESPACE_RE.sub("-", stripped.lower())


def is_informal(uri: str) -> bool:
    """Return True if the URI does not use the formal stigmem:// scheme."""
    return not uri.startswith("stigmem://")
